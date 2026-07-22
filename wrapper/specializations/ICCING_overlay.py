import os
import random
from stages.overlay import Overlay
from utils.db import insert_overlay
import subprocess

class ICCINGOverlay(Overlay):
    def __init__(self, config, db_connection):
        self.config = config
        self.db_connection = db_connection

    def validate(self, event_id):
        #check for default paths
        if self.config['input']['overlay']['parameters']['paths']['results_directory'] == 'default':
            self.config['input']['overlay']['parameters']['paths']['results_directory'] = os.path.join(self.config['global']['output'], f"event_{event_id}", 'iccing')
        if self.config['input']['overlay']['parameters']['paths']['EoS'] == 'default':
            self.config['input']['overlay']['parameters']['paths']['EoS'] = os.path.join(self.config['global']['tmp'], f"event_{event_id}", "tables","ICCING","derv21.dat")
        if self.config['input']['overlay']['parameters']['paths']['quark_chemistry'] == 'default':
            self.config['input']['overlay']['parameters']['paths']['quark_chemistry'] = os.path.join(self.config['global']['tmp'], f"event_{event_id}", "tables","ICCING","GBW_Chemistry.dat")
        if self.config['input']['overlay']['parameters']['paths']['background_attractor'] == 'default':
            self.config['input']['overlay']['parameters']['paths']['background_attractor'] = os.path.join(self.config['global']['tmp'], f"event_{event_id}", "tables","ICCING","BackgroundAttractorRTA.txt")
        if self.config['input']['overlay']['parameters']['paths']['greens_functions'] == 'default':
            self.config['input']['overlay']['parameters']['paths']['greens_functions'] = os.path.join(self.config['global']['tmp'], f"event_{event_id}", "tables","ICCING","GreensFunctionsRTA_New.txt")
        #check for default trento dir
        #check if trento module is enabled
        if self.config['input']['initial_conditions']['type'] == 'Trento': 
            if self.config['input']['overlay']['parameters']['paths']['trento_results_directory'] == 'default':
                self.config['input']['overlay']['parameters']['paths']['trento_results_directory'] = os.path.join(self.config['global']['output'], f"event_{event_id}", 'trento')
            #check if the kind of input/output (sparse) matches 
            if self.config['input']['initial_conditions']['parameters']['sparse-output'] == True:
                if self.config['input']['overlay']['parameters']['input_type'] != 'sparse':
                    print("Warning: Initial condition output type is sparse, but overlay input type is not. Setting overlay input type to sparse.")
                    self.config['input']['overlay']['parameters']['input_type'] = 'sparse'
            if self.config['input']['initial_conditions']['parameters']['sparse-output'] == True:
                if self.config['input']['overlay']['parameters']['output_type'] != 'sparse':
                    print("Warning: Initial condition output type is sparse, but overlay output type is not. Setting overlay output type to sparse.")
                    self.config['input']['overlay']['parameters']['output_type'] = 'sparse'
            #set normalization to one, if not set
            if self.config['input']['initial_conditions']['parameters']['normalization'] != 1.:
                raise ValueError("Trento normalization must be 1.0 for ICCING overlay.")
        else:
            if self.config['input']['overlay']['parameters']['paths']['trento_results_directory'] == 'default':
                raise ValueError("trento_results_directory is set to default, but no Trento module is enabled, path to trento results directory must be provided.")
            
        #check output type, if not sparse, warn and set to sparse
        if self.config['input']['overlay']['parameters']['input_type'] != 'sparse':
            print("Warning: Overlay input type is not sparse, setting it to sparse.")
            self.config['input']['overlay']['parameters']['input_type'] = 'sparse'
        
        pre_type = (self.config['input'].get('preequilibrium', {}) or {}).get('type')
        if isinstance(pre_type, str):
            pre_type = pre_type.lower()
        if pre_type not in (None, 'none'):
            raise ValueError("Preequilibrium type must be 'none' when using ICCING overlay.")


        print("Validation of ICCING overlay configuration completed successfully.")

    def generate_seed(self):
        """Check if a seed is provided; if set to random, generate a random seed."""
        if self.config['input']['overlay']['parameters']['seed'] == 'random':
            seed = random.randint(0, 2**31 - 1)
            print(f"Generated random seed for ICCING: {seed}")
        else:
            seed = self.config['input']['overlay']['parameters']['seed']
            print(f"Using provided seed for ICCING: {seed}")
        return seed

    def create_temp_config(self, seed, event_id):
        """Create a temporary ICCING configuration file using the YAML-provided parameters."""
        overlay_params = self.config['input']['overlay']['parameters']
        paths = self.config['input']['overlay']['parameters']['paths']
    
        # Define output directories for the event
        output_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'iccing')
        os.makedirs(output_dir, exist_ok=True)
    
        config_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'configs')
        os.makedirs(config_dir, exist_ok=True)
    
        # Configuration file path
        config_file_path = os.path.join(config_dir, 'iccing_config.dat')
    
        # Write the configuration file
        with open(config_file_path, 'w') as f:
            # Required paths and settings
            f.write(f"trento_input_dir {paths['trento_results_directory']}/\n")
            f.write(f"output_dir {paths['results_directory']}/\n")
            f.write(f"eos_file {paths['EoS']}\n")
            f.write(f"quark_input_file {paths['quark_chemistry']}\n")
            f.write(f"input_type {1 if overlay_params['input_type'] == 'sparse' else 0}\n")
            f.write(f"output_type {1 if overlay_params['output_type'] == 'sparse' else 0}\n")
            f.write(f"density_profile_type {overlay_params['density_profile_type']}\n")
            f.write(f"greens_evolution {1 if overlay_params['greens_evolution'] else 0}\n")
            f.write(f"perturbative_regime {overlay_params['perturbative_regime']}\n")
            f.write(f"seed_ {seed}\n")
            f.write(f"charge_type {overlay_params['charge_type']}\n")
            f.write(f"eccentricity_type {overlay_params['eccentricity_type']}\n")
            f.write(f"dipole_model {overlay_params['dipole_model']}\n")
    
            # Event-specific settings
            f.write(f"first_event 0\n")
            f.write(f"last_event {self.config['global']['nevents'] - 1}\n")
            f.write(f"grid_max {self.config['global']['grid']['x_max']}\n")
            f.write(f"grid_step {self.config['global']['grid']['step_x']}\n")
    
            # Overlay-specific settings
            f.write(f"kappa_ {overlay_params['kappa']}\n")
            f.write(f"alpha_s {overlay_params['alpha_s']}\n")
            f.write(f"s_chop {overlay_params['s_chop']}\n")
            f.write(f"a_trento {overlay_params['trento_normalization']}\n")
            f.write(f"lambda_ {overlay_params['lambda']}\n")
            f.write(f"lambda_bym {overlay_params['lambda_bym']}\n")
            f.write(f"r_max {overlay_params['r_max']}\n")
            f.write(f"alpha_min {overlay_params['alpha_min']}\n")
            f.write(f"e_thresh {overlay_params['e_thresh']}\n")
            f.write(f"rad_ {overlay_params['gluon_radius']}\n")
            f.write(f"qrad_ {overlay_params['quark_radius']}\n")
            f.write(f"tau_0 {self.config['global']['tau_hydro']}\n")
            f.write(f"t_a {1 if overlay_params['t_a'] else 0}\n")
            f.write(f"t_b {1 if overlay_params['t_b'] else 0}\n")
            f.write(f"background_attractor_file {paths['background_attractor']}\n")
            f.write(f"greens_functions_file {paths['greens_functions']}\n")
            f.write(f"background_points {overlay_params['background_points']}\n")
            f.write(f"greens_functions_points {overlay_params['greens_functions_points']}\n")
            f.write(f"greens_functions_chuncks {overlay_params['greens_functions_chunks']}\n")
            f.write(f"c_infinity {overlay_params['c_infinity']}\n")
            f.write(f"eta_over_s {overlay_params['eta_over_s']}\n")
            f.write(f"tau_hydro {self.config['global']['tau_hydro']}\n")
    
        print(f"ICCING config file created at {config_file_path}")
        return config_file_path
    def run(self, event_id):
        """Run the ICCING overlay using the generated configuration."""

        # Generate seed and create config file
        seed = self.generate_seed()
        config_file_path = self.create_temp_config(seed, event_id)
        # go to TMP dir 
        os.chdir(os.path.join(self.config['global']['tmp'], f"event_{event_id}"))
        # Execute the ICCING overlay program
        executable_path = self.config['global']['basedir'] + '/models/ICCING/iccing'
        command = f"{executable_path} {config_file_path}"
        print(f"Running ICCING overlay with command: {command}")
        subprocess.run([executable_path, config_file_path], check=True)

        #output_file = os.path.join(os.path.dirname(config_file_path), f'iccing_output_{event_id}.txt')
        # Parse the output for eccentricities and insert them into the database
        #eps2, eps3, eps4, eps5 = self.parse_output(output_file)

        eps2, eps3, eps4, eps5 = self.parse_output(os.path.join(self.config['global']['output'], f"event_{event_id}", 'iccing', f'energy_eccentricities.dat'))
        insert_overlay(self.db_connection, event_id, seed, "ICCING")

        print(f"ICCING overlay completed for event {event_id}.")
        
    def parse_output(self, output_file):
        """Parse the eccentricity output to extract eps2, eps3, eps4, and eps5 from the positive charge file."""
        eps2, eps3, eps4, eps5 = 0.0, 0.0, 0.0, 0.0  # Default values in case parsing fails

        try:
            with open(output_file, 'r') as f:
                for line in f:
                    # Split line into values, ignore event number
                    data = line.strip().split()
                    if len(data) >= 14:  # Ensure enough values exist to parse
                        eps2 = float(data[2])  # 1st harmonic magnitude
                        eps3 = float(data[5])  # 2nd harmonic magnitude
                        eps4 = float(data[8])  # 3rd harmonic magnitude
                        eps5 = float(data[11])  # 4th harmonic magnitude
                    else:
                        print(f"Warning: Line in {output_file} does not contain enough data to extract eccentricities.")
                        continue

        except FileNotFoundError:
            print(f"Warning: Eccentricity output file {output_file} not found. Using default eccentricity values.")

        return eps2, eps3, eps4, eps5