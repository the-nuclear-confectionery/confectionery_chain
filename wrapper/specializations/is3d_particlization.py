import os
import shutil
import random
import subprocess
from stages.particlization import Particlization
from utils.db import insert_particlization


class iS3DParticlization(Particlization):
    def validate(self, event_id):
        #check dimension by grid

        #check if hydro module is present
        if self.config['input']['hydrodynamics']['type'] == None:
            #check if input file is set 
            if self.config['input']['particlization']['parameters']['input_file'] == 'default':
                raise ValueError("When no hydro module is used, the freeze-out surface file must be set.")
            else:
                #warning for reading from file, recommend to change 
                #mode, df_mode,  and the includes for the dissipatives quantities
                print("Warning: No hydro module is used, reading from file. Consider changing mode, df_mode, and the includes for the dissipatives quantities to match your setup.")

        elif self.config['input']['hydrodynamics']['type'] == 'CCAKE':
            if self.config['input']['particlization']['parameters']['input_file']  == 'default':
                surface_file = os.path.join(self.config['global']['output'], f"event_{event_id}", "ccake", "freeze_out.dat")
                #set config 
                self.config['input']['particlization']['parameters']['input_file']  = surface_file
            #check for hydro dimensions
            if self.config['input']['hydrodynamics']['initial_conditions']['dimension'] == 2:
                self.config['input']['particlization']['parameters']['mode'] = 8
            elif self.config['input']['hydrodynamics']['initial_conditions']['dimension'] == 3:
                self.config['input']['particlization']['parameters']['mode'] = 9
            else:
                raise ValueError("Hydro dimensions must be 2 or 3 for iS3D particlization.")



        print("iS3D particlization validation passed.")

    #seed generator
    def generate_seed(self):
        """Check if a seed is provided; if set to random, generate a random seed."""
        if self.config['input']['particlization']['parameters']['seed'] == 'random':
            seed = random.randint(0, 2**31 - 1)
            print(f"Generated random seed for iS3D: {seed}")
        else:
            seed = self.config['input']['particlization']['parameters']['seed']
            print(f"Using provided seed for iS3D: {seed}")
        return seed

    def run(self, event_id):
        seed = self.generate_seed()
        self.create_temp_config(seed, event_id)

        # Step 1: Create the temp working directory
        tmpdir = os.path.join(self.config['global']['tmp'], f"event_{event_id}", "iS3D")
        os.makedirs(tmpdir, exist_ok=True)

        # Step 2: Create input and output directories
        input_dir = os.path.join(tmpdir, "input")
        output_dir = os.path.join(tmpdir, "results")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Step 3: Copy the freeze-out surface file to the input directory
        surface_file = self.config['input']['particlization']['parameters']['input_file']
        renamed_surface_file = os.path.join(input_dir, "surface.dat")
        shutil.copy(surface_file, renamed_surface_file)


        # Step 4: Copy the iS3D executable to the temporary directory
        is3d_executable = os.path.join(self.config['global']['basedir'], "models", "iS3D", f"iS3D")
        #print executable
        print(f"iS3D executable: {is3d_executable}")
        tmp_is3d_executable = os.path.join(tmpdir, os.path.basename(is3d_executable))
        shutil.copy(is3d_executable, tmp_is3d_executable)
        os.chmod(tmp_is3d_executable, 0o755)  # Ensure the executable has proper permissions

        #copy the config file and iS3D tables 
        config_file = os.path.join(self.config['global']['output'], f"event_{event_id}", "configs", "iS3D_parameters.dat")
        shutil.copy(config_file, tmpdir)
        shutil.copytree(os.path.join(self.config['global']['basedir'], "tables", "iS3D"), tmpdir,dirs_exist_ok=True)

        command = ["./iS3D"]

        print(f"Running command: {' '.join(command)} in {tmpdir}")
        
        # Run the command in the temporary directory
        result = subprocess.run(command, cwd=tmpdir)

        #insert the particlization results into the database
        insert_particlization(
            self.db_connection,
            event_id=event_id,
            seed=seed,
            particlization_type=self.config['input']['particlization']['type'],
            nsamples=self.config['input']['particlization']['parameters']['max_num_samples'],
        )
        # copy the file in output_dir to global outputs
        #copy the output to the global output directory
        shutil.copytree(output_dir, os.path.join(self.config['global']['output'], f"event_{event_id}", "iS3D"), dirs_exist_ok=True)

        # persist the particle list to the top-level output dir so it survives
        # end-of-run cleanup. Controlled by the per-stage 'keep_result' flag.
        keep_result = self.config['input']['particlization']['parameters'].get('keep_result', False)
        if keep_result:
            particle_list_src = os.path.join(output_dir, "particle_list_osc.dat")
            if os.path.exists(particle_list_src):
                dest = os.path.join(self.config['global']['output'], f"particle_list_osc_{event_id}.dat")
                shutil.copy2(particle_list_src, dest)
                print(f"Persisted particle list to {dest}")




    def create_temp_config(self, seed, event_id):
        """
        Write the IS3D particlization parameters to a config file.
        :param params: Dictionary of IS3D-specific particlization parameters.
        :param output_file: Path to the output config file.
        """
        output_dir = os.path.join(self.config['global']['output'],f"event_{event_id}", "configs")
        os.makedirs(output_dir, exist_ok=True)

        output_file = os.path.join(self.config['global']['output'], f"event_{event_id}", "configs", "iS3D_parameters.dat")
        params = self.config['input']['particlization']['parameters']

        with open(output_file, 'w') as f:
            f.write(f"operation\t= {params['operation']}\n")
            f.write(f"mode\t= {params['mode']}\n")
            f.write(f"hrg_eos\t= {params['hrg_eos']}\n")
            f.write(f"set_FO_temperature\t= {params['set_FO_temperature']}\n")
            f.write(f"T_switch\t= {params['T_switch']}\n")
            f.write(f"dimension\t= {params['dimension']}\n")
            f.write(f"df_mode\t= {params['df_mode']}\n")
            f.write(f"include_baryon\t= {params['include_baryon']}\n")
            f.write(f"include_bulk_deltaf\t= {params['include_bulk_deltaf']}\n")
            f.write(f"include_shear_deltaf\t= {params['include_shear_deltaf']}\n")
            f.write(f"include_baryondiff_deltaf\t= {params['include_baryondiff_deltaf']}\n")
            f.write(f"regulate_deltaf\t= {params['regulate_deltaf']}\n")
            f.write(f"outflow\t= {params['outflow']}\n")
            f.write(f"deta_min\t= {params['deta_min']}\n")
            f.write(f"group_particles\t= {params['group_particles']}\n")
            f.write(f"particle_diff_tolerance\t= {params['particle_diff_tolerance']}\n")
            f.write(f"mass_pion0\t= {params['mass_pion0']}\n")
            f.write(f"do_resonance_decays\t= {params['do_resonance_decays']}\n")
            f.write(f"lightest_particle\t= {params['lightest_particle']}\n")
            f.write(f"oversample\t= {params['oversample']}\n")
            f.write(f"min_num_hadrons\t= {params['min_num_hadrons']}\n")
            f.write(f"max_num_samples\t= {params['max_num_samples']}\n")
            f.write(f"fast\t= {params['fast']}\n")
            f.write(f"y_cut\t= {params['y_cut']}\n")
            f.write(f"sampler_seed\t= {seed}\n")
            f.write(f"test_sampler\t= {params['test_sampler']}\n")
            f.write(f"pT_lower_cut\t= {params['pT_lower_cut']}\n")
            f.write(f"pT_upper_cut\t= {params['pT_upper_cut']}\n")
            f.write(f"pT_bins\t= {params['pT_bins']}\n")
            f.write(f"y_bins\t= {params['y_bins']}\n")
            f.write(f"eta_cut\t= {params['eta_cut']}\n")
            f.write(f"eta_bins\t= {params['eta_bins']}\n")
            f.write(f"tau_min\t= {params['tau_min']}\n")
            f.write(f"tau_max\t= {params['tau_max']}\n")
            f.write(f"tau_bins\t= {params['tau_bins']}\n")
            f.write(f"r_min\t= {params['r_min']}\n")
            f.write(f"r_max\t= {params['r_max']}\n")
            f.write(f"r_bins\t= {params['r_bins']}\n")