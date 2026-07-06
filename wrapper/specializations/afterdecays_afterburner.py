import os
import shutil
import subprocess
from stages.afterburner import Afterburner
from utils.db import insert_afterburner


class AfterdecaysAfterburner(Afterburner):
    def __init__(self, config, db_connection):
        self.config = config
        self.db_connection = db_connection

    def validate(self, event_id: int):
        """
        Ensure required paths exist; fill sensible defaults if set to 'default'.
        """
        p = self.config['input']['afterburner']['parameters']

        # Defaults (reuse analytical_cooperfrye input folder)
        basis_dir = os.path.join(
            self.config['global']['basedir'],
            "models", "analytical_cooperfrye", "input"
        )
        if p.get('path_to_pT_range', 'default') == 'default':
            p['path_to_pT_range'] = os.path.join(basis_dir, "gl15.dat")
        if p.get('path_to_phi_range', 'default') == 'default':
            p['path_to_phi_range'] = os.path.join(basis_dir, "gq20.dat")
        if p.get('path_to_resonances', 'default') == 'default':
            p['path_to_resonances'] = os.path.join(basis_dir, "resoweakPDG2016Plus.dat")

        if p.get('path_to_spectra', 'default') == 'default':
            #check if particlization is none:
            if self.config['input']['particlization']['type'] == 'none':
                raise ValueError("afterdecays requires 'path_to_spectra'")
            elif self.config['input']['particlization']['type'] != 'analytical':
                raise ValueError("afterdecays can only be used with analytical particlization")
            else:
                path = os.path.join(self.config['global']['output'], f"event_{event_id}", "analytical")
                self.config['input']['afterburner']['parameters']['path_to_spectra_corrected'] = os.path.join(path, "corrected_spectra.dat")
                self.config['input']['afterburner']['parameters']['path_to_spectra_uncorrected'] = os.path.join(path, "uncorrected_spectra.dat")
                
        # Default output path
        if p.get('path_to_output', 'default') == 'default':
            #create afterdecays folder
            os.makedirs(os.path.join(self.config['global']['output'], f"event_{event_id}", "afterdecays"), exist_ok=True)
            p['path_to_output'] = os.path.join(
                self.config['global']['output'], f"event_{event_id}", "afterdecays", "output.dat"
            )


        print("Validation of afterdecays configuration completed successfully.")

    def create_temp_config(self, event_id: int, tmpdir: str):
        """
        Write the minimal config file the ./decays program reads.
        Also stores a provenance copy under output/event_<id>/configs.
        """
        p = self.config['input']['afterburner']['parameters']
        # set path to spectra as the input one 
        # temp runtime config (used by the binary)
        cfg_tmp_path = os.path.join(tmpdir, "input.yaml")
        #check if use corrected or not
        if p.get('use_corrected', True):
            p['path_to_spectra'] = p['path_to_spectra_corrected']
        else:
            p['path_to_spectra'] = p['path_to_spectra_uncorrected']

        with open(cfg_tmp_path, 'w') as f:
            f.write(f"path_to_pT_range: {p['path_to_pT_range']}\n")
            f.write(f"path_to_phi_range: {p['path_to_phi_range']}\n")
            f.write(f"path_to_spectra: {p['path_to_spectra']}\n")
            f.write(f"path_to_resonances: {p['path_to_resonances']}\n")
            f.write(f"path_to_output: {p['path_to_output']}\n")

        # provenance copy under output/configs
        cfg_dir = os.path.join(
            self.config['global']['output'], f"event_{event_id}", "configs"
        )
        os.makedirs(cfg_dir, exist_ok=True)
        cfg_out_path = os.path.join(cfg_dir, "afterdecays_parameters.yaml")
        shutil.copy(cfg_tmp_path, cfg_out_path)

        print(f"afterdecays config file created at {cfg_tmp_path}")
        return cfg_tmp_path

    def run(self, event_id: int):
        #create output folder
        # Validate & prepare temp folder
        self.validate(event_id)
        tmpdir = os.path.join(self.config['global']['tmp'], f"event_{event_id}", "afterdecays")
        os.makedirs(tmpdir, exist_ok=True)
        #create event_0 folder
        os.makedirs(os.path.join(tmpdir, f"event_0"), exist_ok=True)
        #create corrected and uncorrected
        os.makedirs(os.path.join(tmpdir, f"event_0", "corrected_spectra"), exist_ok=True)
        os.makedirs(os.path.join(tmpdir, f"event_0", "uncorrected_spectra"), exist_ok=True)
        #copy and rename the correct and uncorrected
        shutil.copy(
            self.config['input']['afterburner']['parameters']['path_to_spectra_corrected'],
            os.path.join(tmpdir, f"event_0", "corrected_spectra", "bsqsbv_dNdpdphi.dat")
        )
        shutil.copy(
            self.config['input']['afterburner']['parameters']['path_to_spectra_uncorrected'],
            os.path.join(tmpdir, f"event_0", "uncorrected_spectra", "bsqsbv_dNdpdphi.dat")
        )

        # Copy executable to temp
        exe_src = os.path.join(
            self.config['global']['basedir'], "models", "decays", "build", "decays"
        )
        exe_tmp = os.path.join(tmpdir, "decays")
        shutil.copy(exe_src, exe_tmp)
        os.chmod(exe_tmp, 0o755)


        # Write temp config
        cfg_tmp_path = self.create_temp_config(event_id, tmpdir)

        # Run ./decays -i input.yaml
        print(f"Running afterdecays with: {exe_tmp} -i {cfg_tmp_path}")
        subprocess.run([exe_tmp, "-i", cfg_tmp_path], cwd=tmpdir, check=True)

        # persist the decayed spectra output to the top-level output dir so it
        # survives end-of-run cleanup. Controlled by the per-stage
        # 'keep_result' flag.
        keep_result = self.config['input']['afterburner']['parameters'].get('keep_result', False)
        if keep_result:
            output_src = self.config['input']['afterburner']['parameters']['path_to_output']
            if os.path.exists(output_src):
                dest = os.path.join(self.config['global']['output'], f"afterdecays_output_{event_id}.dat")
                shutil.copy2(output_src, dest)
                print(f"Persisted afterdecays output to {dest}")

        # Insert DB record (no RNG seed; use -1)
        insert_afterburner(
            self.db_connection,
            event_id=event_id,
            seed=-1,
            afterburner_type=self.config['input']['afterburner']['type'],
        )

        print(f"afterdecays completed for event {event_id}.")
