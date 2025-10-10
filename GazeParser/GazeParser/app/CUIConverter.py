import GazeParser
import GazeParser.Converter as Converter
import GazeParser.Configuration as Configuration
import argparse
import sys
import glob
import os
import traceback

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description='GazeParser commandline data converter for SimpleGazeTracker and PsychoPy-Tobii-Controller data')
    arg_parser.add_argument('input', type=str, help='input data file (accepts wildcard)')
    arg_parser.add_argument('--type', '-t', help='input type (if not specified, guessed from file extension)\n\tsgt: SimpleGazeTracker CSV file\n\tptc: PsychoPy-Tobii-Controller TSV file')
    arg_parser.add_argument('--output', '-o', type=str, help='output file (input must be a single file)')
    arg_parser.add_argument('--config', '-c', type=str, help='camera parameters file')
    arg_parser.add_argument('--overwrite', action='store_true', help='force overwrite ')
    arg_parser.add_argument('--usefileparam', action='store_true', help='[for SimpleGazeTracker CSV] use parameters embedded in the data file')
    arg_parser.add_argument('--unitcnv', type=str, help='[for PsychoPy-Tobbi-Controller TSV] unit conversion (only \'height2pix\' is supported and )')
    args = arg_parser.parse_args()

    input_files = glob.glob(args.input)
    if len(input_files) > 1 and (args.output is not None):
        print('ERROR: --output doesn\'t work with multiple input files.')
        sys.exit()
    
    if args.type is not None:
        if args.type not in ['sgt', 'ptc']:
            print('ERROR: type must be "sgt" or "ptc".')

    if args.config is None:
        config = GazeParser.config
    else:
        # read from file
        try:
            config = Configuration.Config(args.config)
            print('INFO: Open {} as a GazeParser configuration file.'.format(args.config))
        except:
            traceback.print_exc()
            print('ERROR: Could not open {} as a GazeParser configuration file.'.format(args.config))
            sys.exit()

    for input_file in input_files:
        if args.type is None:
            ext = os.path.splitext(input_file)[1].lower()
            if ext == '.csv':
                data_type = 'sgt'
            elif ext == '.tsv':
                data_type = 'ptc'
            else:
                print('ERROR: extension of the input file must be .csv or .tsv if --type option is not specified (input file is {}).'.format(input_file))
                continue
        else:
            data_type = (args.type).lower()
        print('{}: '.format(input_file), end='')
        if data_type == 'sgt':
            ret = Converter.TrackerToGazeParser(inputfile=input_file, config=config, overwrite=args.overwrite, useFileParameters= args.usefileparam, outputfile=args.output)
        elif data_type == 'ptc':
            ret = Converter.PTCToGazeParser(inputfile=input_file, config=config, overwrite=args.overwrite, unitcnv=args.unitcnv, outputfile=args.output)
        print(ret)
