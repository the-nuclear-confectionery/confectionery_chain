import os
import subprocess
from stages.overlay import Overlay
from utils.db import insert_overlay


class AmptGenesisOverlay(Overlay):
    def __init__(self, config, db_connection):
        super().__init__(config, db_connection)
        self.config = config
        self.db_connection = db_connection
    def validate(self, event_id):
        
        # Check if it is 3D by step eta
        if self.config['global']['grid']['step_eta'] == 0:
            raise ValueError("step_eta must be different from 0 for AMPTGenesis")
        
        #resolve a relative overlay input path against basedir (so a repo-relative
        # path like sample_run/AMPT_evt0008/ana works from any working directory)
        _inp = self.config['input']['overlay']['parameters']['paths']['input']
        if _inp not in (None, "default") and not os.path.isabs(_inp):
            self.config['input']['overlay']['parameters']['paths']['input'] = \
                os.path.join(self.config['global']['basedir'], _inp)

        #check if initial condition is AMPT (main.py normalizes the string 'none' to Python None)
        if self.config['input']['initial_conditions']['type'] in (None, "none"):
            #check if input path is default
            if self.config['input']['overlay']['parameters']['paths']['input'] == "default":
                raise ValueError("input path must be set for AMPTGenesis when initial condition is none")
        else:
            if self.config['input']['initial_conditions']['type'] != "ampt":
                raise ValueError("Initial condition must be AMPT for AMPTGenesis or none")
            else:
                #check if input path is default
                if self.config['input']['overlay']['parameters']['paths']['input'] == "default":
                    path = os.path.join(self.config['global']['output'], f"event_{event_id}", 'ampt')
                    self.config['input']['overlay']['parameters']['paths']['input'] = path
        
        #set default output path
        if self.config['input']['overlay']['parameters']['paths']['output'] == "default":
            self.config['input']['overlay']['parameters']['paths']['output'] = os.path.join(self.config['global']['output'], f"event_{event_id}", 'amptgenesis','amptgenesis.dat')
            
        if self.config['input']['preequilibrium']['type'] not in (None, 'none'):
                        raise ValueError("Preequilibrium type must be 'none' when using AMPTGenesis overlay.")
    def create_amptgenesis_config(self, event_id):
        """
        Create an AMPTGenesis configuration file using YAML-provided parameters.
        The configuration file is written with sections like [npoints], [side_size], etc.
        """
        if self.config['input']['overlay']['type'] != 'AMPTGenesis':
            raise ValueError("create_amptgenesis_config should only be called for AMPTGenesis.")

        params = self.config['input']['overlay']['parameters']
        output_dir = os.path.join(self.config['global']['output'],"event_" + str(event_id), 'configs')
        os.makedirs(output_dir, exist_ok=True)
        config_file_path = os.path.join(output_dir, 'amptgenesis.cfg')
        with open(config_file_path, 'w') as f:
            # Section [npoints]
            #calculate npoints from global maximum and step (division +1)
            npoints_x = int(2.*(int(self.config['global']['grid']['x_max'] / self.config['global']['grid']['step_x']) + 1 ))
            npoints_y = int(2.*(int(self.config['global']['grid']['y_max'] / self.config['global']['grid']['step_y']) + 1 ))
            npoints_eta =int(2.*(int(self.config['global']['grid']['eta_max'] / self.config['global']['grid']['step_eta']) + 1))

            #calculate size_side from global maximum 
            size_side_x = self.config['global']['grid']['x_max']*2.
            size_side_y = self.config['global']['grid']['y_max']*2.
            size_side_eta = self.config['global']['grid']['eta_max']*2.

            f.write("[npoints]\n")
            f.write(f"x = {npoints_x}\n")
            f.write(f"y = {npoints_y}\n")
            f.write(f"eta = {npoints_eta}\n\n")
            # Section [side_size]
            f.write("[side_size]\n")
            f.write(f"x = {size_side_x}\n")
            f.write(f"y = {size_side_y}\n")
            f.write(f"eta = {size_side_eta}\n\n")

            # Section [paths]
            f.write("[paths]\n")
            f.write(f"input = {params['paths']['input']}\n")
            f.write(f"output = {params['paths']['output']}\n\n")

            # Section [smearing]
            f.write("[smearing]\n")
            f.write(f"sigma_r = {params['smearing']['sigma_r']}\n")
            f.write(f"sigma_eta = {params['smearing']['sigma_eta']}\n")
            f.write(f"K = {params['smearing']['K']}\n")
            f.write(f"tau0 = {self.config['global']['tau_hydro']}\n")

        print(f"AMPTGenesis config file created at {config_file_path}")
        return config_file_path
    
    def run(self, event_id):

        #create amptgenesis config
        self.create_amptgenesis_config(event_id)

        ampt_executable = self.config['global']['basedir'] + "/models/AMPTGenesis/build/AMPT-Genesis.exe"
        output_dir = os.path.join(self.config['global']['output'],"event_" + str(event_id))
        config_file_path = os.path.join(output_dir, 'configs', 'amptgenesis.cfg')

        #create output file dir
        output_file_dir = os.path.dirname(self.config['input']['overlay']['parameters']['paths']['output'])
        os.makedirs(output_file_dir, exist_ok=True)
    

        #run amptgenesis
        subprocess.run(
            [ampt_executable, "--genesis-config", config_file_path],
            check=True  # Raises an error if the command fails
        )

        #convert amptgenesis format to ccake
        self.convert_amptgenesis_format(os.path.join(output_dir, 'amptgenesis', 'amptgenesis.dat'), os.path.join(output_dir, 'amptgenesis', 'ccake_ic.dat'))

        #insert overlay in db
        insert_overlay(
            self.db_connection,
            event_id,
            0,                 # seed
            "AMPTGenesis"
        )

    def convert_amptgenesis_format(self, input_file, output_file):
        # Current AMPTGenesis writes the CCAKE IC format DIRECTLY (first line
        # "#0 stepx stepy stepEta 0 xmin ymin etamin"), not the older native format
        # with "Lx="/"Ly="/"Leta=" header lines this function was written for. In that
        # case pass it through unchanged (as the paper convergence runs did — CCAKE
        # loads the IC as written; input_initial_shear/bulk in the CCAKE config decide
        # what is used).
        with open(input_file) as _f:
            _first = _f.readline()
        if _first.startswith("#0"):
            import shutil
            shutil.copyfile(input_file, output_file)
            return

        # Initialize variables to hold header information
        nx = ny = neta = Lx = Ly = Leta = None
        xmin = ymin = etamin = None
        header_prefix = "#"
        column_line_found = False  # To track and skip the column header line

        # Read input file line by line
        with open(input_file, 'r') as infile:
            lines = infile.readlines()

        # Extract header information
        for line in lines:
            if line.startswith(header_prefix):
                if "nx" in line:
                    nx = int(line.split('=')[1].strip())
                elif "ny" in line:
                    ny = int(line.split('=')[1].strip())
                elif "neta" in line:
                    neta = int(line.split('=')[1].strip())
                elif "Lx" in line:
                    Lx = float(line.split('=')[1].strip())
                elif "Ly" in line:
                    Ly = float(line.split('=')[1].strip())
                elif "Leta" in line:
                    Leta = float(line.split('=')[1].strip())
                elif "x y eta" in line:  # Detect and mark the column header line
                    column_line_found = True
            elif column_line_found:
                # Stop processing headers after encountering the column header line
                break

        # Calculate step sizes and min values
        stepx = Lx / (nx - 1) if nx else 1
        stepy = Ly / (ny - 1) if ny else 1
        stepEta = Leta / (neta - 1) if neta else 1
        xmin, ymin, etamin = -Lx / 2, -Ly / 2, -Leta / 2

        # Create header for output file
        header_line = f"#0 {stepx} {stepy} {stepEta} 0 {xmin} {ymin} {etamin}\n"

        # Open output file and write header
        with open(output_file, 'w') as outfile:
            outfile.write(header_line)

            # Process and write data lines
            data_start = False  # To skip lines until data starts
            for line in lines:
                if column_line_found and not data_start:
                    # Skip the column header line, and set flag when actual data starts
                    column_line_found = False
                    data_start = True
                    continue

                if data_start and not line.startswith(header_prefix):
                    values = list(map(float, line.split()))

                    # Extract necessary values
                    x, y, eta = values[0], values[1], values[2]
                    epsilon, rhob, rhos, rhoq = values[3], values[18], values[29], values[19]
                    ux, uy, ueta = values[4], values[5], values[6]
                    bulk = values[7]  # Assuming trace as bulk pressure
                    pixx, pixy, pixeta = values[12], values[13], values[14]
                    piyy, piyeta, pietaeta = values[15], values[16], values[17]

                    # Write to output file
                    outfile.write(f"{x} {y} {eta} {epsilon} {rhob} {rhos} {rhoq} "
                                f"{ux} {uy} {ueta} {bulk} {pixx} {pixy} {pixeta} "
                                f"{piyy} {piyeta} {pietaeta}\n")
