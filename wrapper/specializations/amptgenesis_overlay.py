import os
import shutil
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

        # Initial condition must be AMPT, or none with an explicit input path.
        # main.py normalizes disabled stages to None, but validate() runs on the
        # raw string for stages later in the chain, so accept both spellings.
        ic_type = (self.config['input'].get('initial_conditions', {}) or {}).get('type')
        if isinstance(ic_type, str):
            ic_type = ic_type.lower()
        paths = self.config['input']['overlay']['parameters']['paths']
        if ic_type in (None, 'none'):
            if paths['input'] == "default":
                raise ValueError("input path must be set for AMPTGenesis when initial condition is none")
        elif ic_type != "ampt":
            raise ValueError("Initial condition must be AMPT for AMPTGenesis or none")
        elif paths['input'] == "default":
            paths['input'] = os.path.join(self.config['global']['output'], f"event_{event_id}", 'ampt')

        #set default output path
        if paths['output'] == "default":
            paths['output'] = os.path.join(self.config['global']['output'], f"event_{event_id}", 'amptgenesis','amptgenesis.dat')

        pre_type = (self.config['input'].get('preequilibrium', {}) or {}).get('type')
        if isinstance(pre_type, str):
            pre_type = pre_type.lower()
        if pre_type not in (None, 'none'):
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
            # Odd count = 2*N+1 so a grid point sits exactly at center (x=0),
            # matching the reference AMPTGenesis configs (e.g. 121 for x_max=12,
            # step=0.2). An even count would straddle the origin.
            grid = self.config['global']['grid']
            npoints_x = 2 * int(grid['x_max'] / grid['step_x']) + 1
            npoints_y = 2 * int(grid['y_max'] / grid['step_y']) + 1
            npoints_eta = 2 * int(grid['eta_max'] / grid['step_eta']) + 1

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
            smearing = params['smearing']
            f.write("[smearing]\n")
            f.write(f"sigma_r = {smearing['sigma_r']}\n")
            f.write(f"sigma_eta = {smearing['sigma_eta']}\n")
            f.write(f"K = {smearing['K']}\n")
            f.write(f"tau0 = {self.config['global']['tau_hydro']}\n")
            f.write(f"backpropagate = {str(smearing.get('backpropagate', False)).lower()}\n\n")

            # The remaining sections were previously omitted, so AMPTGenesis fell
            # back to its internal defaults. Emit them explicitly and wire the
            # coordinate system / diffusion output to the CCAKE config so the IC
            # cannot silently disagree with the hydro that consumes it.
            hydro_ic = self.config['input'].get('hydrodynamics', {}).get('initial_conditions', {}) or {}
            hydro_params = self.config['input'].get('hydrodynamics', {}).get('parameters', {}) or {}
            diffusion = (self.config['input'].get('hydrodynamics', {})
                         .get('hydro', {}).get('viscous_parameters', {})
                         .get('diffusion', {}) or {})

            coord = hydro_ic.get('coordinate_system', 'hyperbolic')
            # CCAKE needs diffusion columns in the IC only if it reads an initial
            # diffusion current; otherwise omit them.
            output_diffusion = diffusion.get('input_initial_diffusion', False)
            # match AMPTGenesis's write-cutoff to CCAKE's particle deletion cutoff
            e_cutoff = params.get('energy_density_cutoff',
                                  hydro_params.get('energy_cutoff', 0.15))
            sample_radius = params.get('sample_radius', {}) or {}

            # Section [sample_radius]
            f.write("[sample_radius]\n")
            f.write(f"xy = {sample_radius.get('xy', 2.0)}\n")
            f.write(f"eta = {sample_radius.get('eta', 2.0)}\n\n")

            # Section [coordinates]
            f.write("[coordinates]\n")
            f.write(f"system = {coord}\n\n")

            # Section [input]
            f.write("[input]\n")
            f.write("format = ampt\n\n")

            # Section [output]
            f.write("[output]\n")
            f.write(f"output_diffusion = {str(output_diffusion).lower()}\n")
            f.write(f"energy_density_cutoff = {e_cutoff}\n")

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

        #insert overlay in db (AMPTGenesis is deterministic given its AMPT
        #input, so it has no seed of its own)
        insert_overlay(self.db_connection, event_id, None, "AMPTGenesis")

    def convert_amptgenesis_format(self, input_file, output_file):
        """Stage AMPTGenesis's output as CCAKE's initial condition file.

        AMPTGenesis's output_to_file() already writes CCAKE's exact IC format:
        a `#0 dx dy deta 0 xmin ymin etamin` grid header followed by
        `x y eta e rhoB rhoS rhoQ ux uy ueta bulk pixx pixy pixeta piyy piyeta
        pietaeta` data rows, with informational `#`-prefixed lines interspersed
        (which CCAKE's read_ccake() skips). No reformatting is needed; this
        just stages it under the path CCAKEHydro expects.
        """
        shutil.copy(input_file, output_file)
