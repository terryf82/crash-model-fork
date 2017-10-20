import json
import os
import csv
import rtree
import pyproj
import argparse

from ATR_util import *

ATR_FP = '../data/raw/AUTOMATED TRAFFICE RECORDING/'
PROCESSED_DATA_FP = '../data/processed/'
atrs = os.listdir(ATR_FP)

PROJ = pyproj.Proj(init='epsg:3857')


def geocode_and_parse():

    if not os.path.exists(PROCESSED_DATA_FP + 'geocoded_atrs.csv'):
        print "No geocoded_atrs.csv found, geocoding addresses"

        # geocode, parse result - address, lat long
        results = []
        for atr in atrs:
            atr = atr
            if is_readable_ATR(ATR_FP + atr):
                atr_address = clean_ATR_fname(ATR_FP + atr)
                print atr_address
                geocoded_add, lat, lng = geocode_address(atr_address)
                print str(geocoded_add) + ',' + str(lat) + ',' + str(lng)
                vol, speed, motos, light, heavy = read_ATR(ATR_FP + atr)
                r = [
                    atr_address,
                    geocoded_add,
                    lat,
                    lng,
                    vol,
                    speed,
                    motos,
                    light,
                    heavy,
                    atr
                ]
                results.append(r)
                print('Number geocoded: {}'.format(len(results)))

        with open(PROCESSED_DATA_FP + 'geocoded_atrs.csv', 'wb') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow([
                'orig',
                'geocoded',
                'lat',
                'lng',
                'volume',
                'speed',
                'motos',
                'light',
                'heavy',
                'filename'
            ])
            for r in results:
                writer.writerow(r)
    else:
        print('geocoded_atrs.csv already exists, skipping geocoding')

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--graph', action='store_true',
                        help='Whether to generating graphs')

    args = parser.parse_args()

    geocode_and_parse()
    # Read in segments
    inter = read_shp(PROCESSED_DATA_FP + 'maps/inters_segments.shp')
    non_inter = read_shp(PROCESSED_DATA_FP + 'maps/non_inters_segments.shp')
    print "Read in {} intersection, {} non-intersection segments".format(len(inter), len(non_inter))

    # Combine inter + non_inter
    combined_seg = inter + non_inter

    # # Create spatial index for quick lookup
    segments_index = rtree.index.Index()
    for idx, element in enumerate(combined_seg):
        segments_index.insert(idx, element[0].bounds)

    print('Created spatial index')

    # Read in atr lats
    atrs = csv_to_projected_records(PROCESSED_DATA_FP + 'geocoded_atrs.csv',
                                    x='lng', y='lat')
    print "Read in data from {} atrs".format(len(atrs))

    if args.graph:
        # Generate sparkline graph of traffic distribution
        files = [ATR_FP +
                 atr['properties']['filename'] for atr in atrs]
        all_counts = get_hourly_rates(files)
        plot_hourly_rates(all_counts,
                        os.path.abspath(PROCESSED_DATA_FP) + '/atr_dist.png')

    # Find nearest atr - 20 tolerance
    print "Snapping atr to segments"
    find_nearest(atrs, combined_seg, segments_index, 20)

    with open(PROCESSED_DATA_FP + 'snapped_atrs.json', 'w') as f:
        json.dump([x['properties'] for x in atrs], f)

