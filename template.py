#!/usr/bin/env python2.7
###################################################################################################################################################
# Template written by David Cabinian and edited by Ang Deng
# dhcabinian@gatech.edu
# adeng3@gatech.edu
# Written for python 2.7
# Run python template.py --help for information.
###################################################################################################################################################
# DO NOT MODIFY THESE IMPORTS / DO NOT ADD IMPORTS IN THIS NAMESPACE
# Importing a filesystem library such as ['sys', 'os', 'shutil'] will result in loss of all homework points.
###################################################################################################################################################
import argparse
import apache_beam as beam
from apache_beam.io import ReadFromText
from apache_beam.io import WriteToText
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
###################################################################################################################################################

# storing format: <(0)movie_id, (1)title, (2)release year, (3)duration, (4)genre, (5)director id, (6)director, 
# (7)main actor1, (8)main actor2, (9)buy price, (10)rent price, (11)amount, (12)purchase method, (13)user name, (14)transaction time>

def run(args, pipeline_args):
    # INSERT YOUR CODE HERE
    key_field_index = 0
    if args.director_copies_sold or args.director_dollars_sold:
        key_field_index = 5

    def SplitLine(line):
        # split to extract each field in the .csv file
        line_modified = line.replace(', ', '_')
        return line_modified.split(',')


    def PairWithCopies(fields):
        id = fields[key_field_index]
        purchase_method = fields[12]
        amount = fields[11]
        return (id, (amount if purchase_method == 'buy' else 0, amount if purchase_method == 'rent' else 0))


    def PairWithRevenue(fields):
        id = fields[key_field_index]
        revenue = int(fields[9]) if fields[12] == 'buy' else int(fields[10])
        return (id, revenue)


    def PairWithTransaction(fields):
        movie_id = fields[0]
        user_name = fields[13]
        date_time = fields[14]
        return ((user_name, date_time), movie_id)


    def Sum(group):
        from operator import add
        buy_tot = 0
        rent_tot = 0
        (id, records) = group
        for record in records:
            (buy_amt, rent_amt) = record
            buy_tot = buy_tot + int(buy_amt)
            rent_tot = rent_tot + int(rent_amt)
        return (id, buy_tot, rent_tot)


    def Permute(transaction):
        ((user_name, date_time), movie_list) = transaction
        li = []
        position = 0
        for movie_id in movie_list:
            if len(movie_list) > 1:
                for movie_id_other in movie_list:
                    if (movie_id_other != movie_id): li.append(((movie_id, movie_id_other), 1))
            else:
                li.append(((movie_id, None), 0))
        return li


    def ChangeKey(movie_combination):
        #print(movie_combination)
        (movie_id, movie_id_other), count = movie_combination
        return (movie_id, (movie_id_other, count))


    def Sort(movie_and_list):
        from operator import itemgetter
        (movie_id, purchased_together_tuples) = movie_and_list
        highest_list = []
        sorted_list = sorted(purchased_together_tuples, key=itemgetter(1), reverse=True)
        if sorted_list[0][1] == 0:
            highest_list.append(('None', str(0)))
        else:
            i = 0
            while i < len(sorted_list) and sorted_list[i][1] == sorted_list[0][1]:
                highest_list.append(sorted_list[i])
                i = i + 1
        return (movie_id, highest_list)


    def FormatMovieNumbers(result):
        (id, buy_tot, rent_tot) = result
        return '%s\t%s\t%s'% (id, str(buy_tot), str(rent_tot))


    def FormatMovieRevenue(result):
        (id, revenue_tot) = result
        return '%s\t%s'% (id, str(revenue_tot))


    def FormatHighestList(result):
        movie_id, highest_list = result
        li = []
        #print(movie_id)
        li.append(str(movie_id))
        for highest_movie in highest_list:
            #print(highest_movie)
            li.append(str(highest_movie[0]))
        frequency = highest_list[0][1]
        li.append(str(frequency))
        result_formatted = '\t'.join(li)
        return result_formatted


    with beam.Pipeline(options=PipelineOptions(pipeline_args)) as pipeline:
    	lines = pipeline | beam.io.ReadFromText(args.input)
        fields = (
            lines
            | 'Split' >> beam.Map(SplitLine)
        )
        filtered_fields = (
            fields
            | 'Filter' >> beam.Filter(lambda field: args.genre is None and field is not None or args.genre is not None and field[4] == args.genre)
        )

        if args.copies_sold or args.director_copies_sold:
            movie_numbers = (
                filtered_fields
                | 'PairWithCopies' >> beam.Map(PairWithCopies)
                | 'GroupAndSum' >> beam.GroupByKey()
                | 'MergeAmount' >> beam.Map(Sum)
                | 'FormatRenvenue' >> beam.Map(FormatMovieNumbers)
            )
            movie_numbers | 'WriteMovieNumbers' >> beam.io.WriteToText(args.output)

        if args.dollars_sold or args.director_dollars_sold:
            movie_revenue = (
                filtered_fields
                | 'PairWithRevenue' >> beam.Map(PairWithRevenue)
                | 'CombineRevenue' >> beam.CombinePerKey(sum)
                | 'FormatRevenue' >> beam.Map(FormatMovieRevenue)
            )
            movie_revenue | 'WriteMovieRevenue' >> beam.io.WriteToText(args.output)

        if args.purchased_together:
            highest_list = (
                filtered_fields
                | 'PairWithTrnasaction' >> beam.Map(PairWithTransaction) # (user_name, date_time), movie_id
                | 'GroupByTransaction' >> beam.GroupByKey()
                | 'Permute' >> beam.FlatMap(Permute) # (movie_id, movie_id_other), 1
                | 'CombineMovieCombo' >> beam.CombinePerKey(sum)
                | 'ChangeKey' >> beam.Map(ChangeKey) # movie_id, (movie_id_other, count)
                | 'GroupByMovie' >> beam.GroupByKey() # movie_id, [(movie_id_other, count), ... ]
                | 'SortList' >> beam.Map(Sort)
                | 'FormatHighestList' >> beam.Map(FormatHighestList)
            )
            highest_list | 'WriteHighestList' >> beam.io.WriteToText(args.output)

    pass


###################################################################################################################################################
# DO NOT MODIFY BELOW THIS LINE
###################################################################################################################################################
if __name__ == '__main__':
    # This function will parse the required arguments for you.
    # Try template.py --help for more information
    # View https://docs.python.org/3/library/argparse.html for more information on how it works
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description="ECE 6102 Assignment 3", epilog="Example Usages:\npython test.py --input small_dataset.csv --output out.csv --runner Direct --copies_sold\npython test.py --input $BUCKET/input_files/small_dataset.csv --output $BUCKET/out.csv --runner DataflowRunner --project $PROJECT --temp_location $BUCKET/tmp/ --copies_sold")
    parser.add_argument('--input', help="Input file to process.", required=True)
    parser.add_argument('--output', help="Output file to write results to.", required=True)
    parser.add_argument('--project', help="Your Google Cloud Project ID.")
    parser.add_argument('--runner', help="The runner you would like to use for the map reduce.", choices=['Direct', 'DataflowRunner'], required=True)
    parser.add_argument('--temp_location', help="Location where temporary files should be stored.")
    parser.add_argument('--num_workers', help="Set the number of workers for Google Cloud Dataflow to allocate (instead of autoallocation). Default value = 0 uses autoallocation.", default="0")
    pipelines = parser.add_mutually_exclusive_group(required=True)
    pipelines.add_argument('--copies_sold', help="Count the total number of movie purchases and rentals for each movie that has been purchased at least once and order the final result from largest to smallest count.", action='store_true')
    pipelines.add_argument('--dollars_sold', help="Calculate the total dollar amount of sales for each movie and order the final result from largest to smallest amount.", action='store_true')
    pipelines.add_argument('--director_copies_sold', help="Count the total number of number of movie purchases and rentals for each director that has had at least one movie purchased and order the final result from largest to smallest count.", action='store_true')
    pipelines.add_argument('--director_dollars_sold', help="Calculate the total dollar amount of sales for each director and order the final result from largest to smallest amount.", action='store_true')
    pipelines.add_argument('--purchased_together', help="For each movie that was purchased at least once, find the other movie that was purchased most often at the same time and count how many times the two wines were purchased together.", action='store_true')
    parser.add_argument('--genre', help="Use the genre whose first letter is the closest to the first letter of your last name. ", choices=["Action", "Animation", "Comedy", "Documentary", "Drama", "Horror", "Musical", "Sci-Fi"])
    args = parser.parse_args()

    # Separating Pipeline options from IO options
    # HINT: pipeline args go nicely into: options=PipelineOptions(pipeline_args)
    if args.runner  == "DataflowRunner":
        if None in [args.project, args.temp_location]:
            raise Exception("Missing some pipeline options.")
        pipeline_args = []
        pipeline_args.append("--runner")
        pipeline_args.append(args.runner)
        pipeline_args.append("--project")
        pipeline_args.append(args.project)
        pipeline_args.append("--temp_location")
        pipeline_args.append(args.temp_location)
        if args.num_workers != "0":
            # This disables the autoscaling if you have specified a number of workers
            pipeline_args.append("--num_workers")
            pipeline_args.append(args.num_workers)
            pipeline_args.append("--autoscaling_algorithm") 
            pipeline_args.append("NONE")
    else:
        pipeline_args = []


    run(args, pipeline_args)
