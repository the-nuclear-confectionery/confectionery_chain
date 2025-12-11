import os
import random
from stages.afterburner import Afterburner
from utils.db import insert_afterburner
import subprocess

class SMASHAfterburner(Afterburner):
    def __init__(self, config, db_connection):
        self.config = config
        self.db_connection = db_connection

    def validate(self, event_id):

        #check for decays only
        if self.config['input']['afterburner']['parameters']['decays_only'] == True:
            #change params
            self.config['input']['afterburner']['parameters']['Collision_Term']['No_Collisions'] = True
            self.config['input']['afterburner']['parameters']['Collision_Term']['Force_Decays_At_End'] = True
        else:
            #change params
            self.config['input']['afterburner']['parameters']['Collision_Term']['No_Collisions'] = False
            self.config['input']['afterburner']['parameters']['Collision_Term']['Force_Decays_At_End'] = True

        #check for particleziation module
        if self.config['input']['particlization']['type'] == None:
            if self.config['input']['afterburner']['parameters']['input_file']== "default":
                raise ValueError("No particlization module specified, input file and number of samples 'Nevents' must be provided.")
            if self.config['input']['afterburner']['parameters']['General']['Nevents'] == 1:
                print("Warning - Using number of samples 'Nevents' =1, check if matches your setup.")
        elif self.config['input']['particlization']['type'] == 'is3d':
            print("iS3D particlization detected, using particle list from iS3D.")
            if self.config['input']['afterburner']['parameters']['input_file']== "default":
                file_is3d = os.path.join(self.config['global']['output'], f"event_{event_id}", "iS3D", "particle_list_osc.dat")
                self.config['input']['afterburner']['parameters']['input_file'] = file_is3d
            #copy number of samples
            self.config['input']['afterburner']['parameters']['General']['Nevents'] = self.config['input']['particlization']['parameters']['max_num_samples']
        elif self.config['input']['particlization']['type'] == 'BQSSampler':
            print("BQSSampler particlization detected.")
            if self.config['input']['afterburner']['parameters']['input_file']== "default":
                file_bqssampler = os.path.join(self.config['global']['output'], f"event_{event_id}", "BQSSampler", "particle_list.dat")
                self.config['input']['afterburner']['parameters']['input_file'] = file_bqssampler
            #copy number of samples
            self.config['input']['afterburner']['parameters']['General']['Nevents'] = self.config['input']['particlization']['parameters']['samples']
        else:
            raise ValueError("Particlization type not support for SMASH")

        #break input file into dir and file
        input_file = self.config['input']['afterburner']['parameters']['input_file']
        input_dir, input_file = os.path.split(input_file)
        self.config['input']['afterburner']['parameters']['Modi']['List']['File_Directory'] = input_dir
        self.config['input']['afterburner']['parameters']['Modi']['List']['Filename'] = input_file



        print(f"Validation of SMASH configuration completed successfully.")

    def generate_seed(self):
        """Generate a random seed if set to 'random', or use the provided seed."""
        seed = self.config['input']['afterburner']['parameters']['General']['seed']
        if seed == 'random':
            seed = random.randint(0, 2**31 - 1)
            print(f"Generated random seed for SMASH: {seed}")
        else:
            print(f"Using provided seed for SMASH: {seed}")
        return seed

    def create_temp_config(self, seed, event_id):
        """Create a temporary configuration file for SMASH using the YAML-provided parameters."""
        general_params = self.config['input']['afterburner']['parameters']['General']
        output_params = self.config['input']['afterburner']['parameters']['Output']
        collision_params = self.config['input']['afterburner']['parameters']['Collision_Term']
        modi_params = self.config['input']['afterburner']['parameters']['Modi']['List']
        # Define output directories for the event
        output_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'smash')
        os.makedirs(output_dir, exist_ok=True)

        config_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'configs')
        os.makedirs(config_dir, exist_ok=True)

        # Configuration file path
        config_file_path = os.path.join(config_dir, 'smash_config.yaml')

        # Write the configuration file
        with open(config_file_path, 'w') as f:
            f.write(f"Logging:\n")
            f.write(f"  default: {self.config['input']['afterburner']['parameters']['Logging']['default']}\n\n")

            f.write(f"General:\n")
            f.write(f"  Modus: {general_params['Modus']}\n")
            f.write(f"  Time_Step_Mode: {general_params['Time_Step_Mode']}\n")
            f.write(f"  Delta_Time: {general_params['Delta_Time']}\n")
            f.write(f"  End_Time: {general_params['End_Time']}\n")
            f.write(f"  Randomseed: {seed}\n")
            f.write(f"  Nevents: {general_params['Nevents']}\n\n")

            f.write(f"Output:\n")
            f.write(f"  Output_Interval: {output_params['Output_Interval']}\n")
            f.write(f"  Particles:\n")
            f.write(f"    Format: {output_params['Particles']['Format']}\n\n")

            f.write(f"Collision_Term:\n")
            f.write(f"  No_Collisions: {collision_params['No_Collisions']}\n")
            f.write(f"  Force_Decays_At_End: {collision_params['Force_Decays_At_End']}\n\n")

            f.write(f"Modi:\n")
            f.write(f"  List:\n")
            f.write(f"    File_Directory: {modi_params['File_Directory']}\n")
            f.write(f"    Filename: {modi_params['Filename']}\n")

        print(f"SMASH config file created at {config_file_path}")
        return config_file_path

    def run(self, event_id):
        # Validate configuration and generate seed
        seed = self.generate_seed()
        config_file_path = self.create_temp_config(seed, event_id)

        # Define necessary paths
        input_file = self.config['input']['afterburner']['parameters']['input_file']
        input_dir = os.path.dirname(input_file)
        output_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", 'smash')
        output_basedir= os.path.join(self.config['global']['output'], f"event_{event_id}")
        # Navigate to the temporary directory for execution
        os.chdir(os.path.join(self.config['global']['tmp'], f"event_{event_id}"))

        # Build the SMASH command

        command = [
            "smash",
            "-i", config_file_path,
            "-o", output_dir
        ]

        print(f"Running SMASH afterburner with command: {' '.join(command)}")
        subprocess.run(command, check=True)

        print(f"SMASH afterburner completed for event {event_id}.")
        #remove the tabulations generated in the output basedir
        os.system(f"rm -rf {output_basedir}/tabulations")
        #remove copied config file from output dir
        os.system(f"rm -rf {output_dir}/config.yaml")

        #insert into db
        insert_afterburner(
            self.db_connection,
            event_id=event_id,
            seed=seed,
            afterburner_type=self.config['input']['afterburner']['type'],
        )
