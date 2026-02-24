import os
import shutil
import random
import subprocess
from stages.particlization import Particlization
from utils.db import insert_particlization


class BQSSamplerParticlization(Particlization):

    def validate(self, event_id: int):
        hydro = self.config['input'].get('hydrodynamics', {})
        hydro_type = hydro.get('type', None)
        part = self.config['input']['particlization']
        p = part['parameters']

        if hydro_type is None:
            if p.get('input_file', 'default') == 'default':
                raise ValueError("When no hydro module is used, the freeze-out surface file must be set.")
            else:
                print("Warning: No hydro module is used. Ensure mode/df settings and chemical potentials match the surface format.")
        elif hydro_type == 'CCAKE':
            if p.get('input_file', 'default') == 'default':
                surface_file = os.path.join(
                    self.config['global']['output'],
                    f"event_{event_id}",
                    "ccake",
                    "freeze_out.dat"
                )
                p['input_file'] = surface_file

            dim = hydro['initial_conditions']['dimension']
            if dim not in (2, 3):
                raise ValueError("Hydro dimensions must be 2 or 3 for BQSSampler particlization.")
            p['dimension'] = dim
            p['coordinate_system'] = hydro['initial_conditions'].get('coordinate_system')
            p['mode'] = 'ccakev2'

        # Default tables path (used below when copying to tmpdir)
        if p.get('tables_path', 'default') == 'default':
            p['tables_path'] = os.path.join(
                self.config['global']['basedir'],
                "tables",
                "BQSSampler"
            )
        print("BQSSampler particlization validation passed.")

    def generate_seed(self) -> int:
        s = self.config['input']['particlization']['parameters'].get('seed', 'random')
        if s == 'random':
            seed = random.randint(0, 2**31 - 1)
            print(f"Generated random seed for BQSSampler: {seed}")
        else:
            seed = int(s)
            print(f"Using provided seed for BQSSampler: {seed}")
        return seed

    def run(self, event_id: int):
        seed = self.generate_seed()

        # Workspace
        tmpdir = os.path.join(self.config['global']['tmp'], f"event_{event_id}", "BQSSampler")
        os.makedirs(tmpdir, exist_ok=True)

        input_dir = os.path.join(tmpdir, "input")
        output_dir = os.path.join(tmpdir, "results")
        os.makedirs(input_dir, exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)

        # Write config directly into tmpdir and get its path
        cfg_file = self.create_temp_config(seed, event_id, tmpdir)

        # Copy executable to tmpdir and make it executable
        exe_src = os.path.join(
            self.config['global']['basedir'],
            "models", "BQSSampler", "build", "particlizer"
        )
        print(f"BQSSampler executable: {exe_src}")
        exe_tmp = os.path.join(tmpdir, os.path.basename(exe_src))
        shutil.copy(exe_src, exe_tmp)
        os.chmod(exe_tmp, 0o755)

        # Ensure the configured output folder exists (common pattern: write inside tmpdir/results)
        p = self.config['input']['particlization']['parameters']
        out_file = p.get('output_file', None)
        if out_file:
            out_dir = os.path.dirname(out_file)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

        # Run executable with config file
        command = ["./particlizer", os.path.basename(cfg_file)]
        print(f"Running command: {' '.join(command)} in {tmpdir}")
        subprocess.run(command, cwd=tmpdir, check=True)

        # DB record
        nsamples = int(p.get('samples', 0))
        insert_particlization(
            self.db_connection,
            event_id=event_id,
            seed=seed,
            particlization_type=self.config['input']['particlization']['type'],
            nsamples=nsamples,
        )

        # Copy results back to final output
        shutil.copytree(
            output_dir,
            os.path.join(self.config['global']['output'], f"event_{event_id}", "BQSSampler"),
            dirs_exist_ok=True
        )

    def create_temp_config(self, seed: int, event_id: int, tmpdir: str) -> str:
        """
        Write the run-time config into tmpdir and also persist a copy under
        <global.output>/event_<id>/configs for provenance.
        Returns the path to the config in tmpdir.
        """
        # Paths
        run_cfg_file = os.path.join(tmpdir, "BQSSampler_parameters.dat")
        out_cfg_dir = os.path.join(self.config['global']['output'], f"event_{event_id}", "configs")
        os.makedirs(out_cfg_dir, exist_ok=True)
        saved_cfg_file = os.path.join(out_cfg_dir, "BQSSampler_parameters.dat")

        p = self.config['input']['particlization']['parameters']

        # If output_file was left as 'default', point it inside tmpdir/results
        if p.get('output_file', 'default') == 'default':
            p['output_file'] = os.path.join(tmpdir, "results", "particle_list.dat")

        # Helper to write a config to a given path
        def _write_cfg(path: str):
            with open(path, 'w') as f:
                f.write(f"mode {p['mode']}\n")
                f.write(f"coordinate_system {p['coordinate_system']}\n")
                f.write(f"dimension {p['dimension']}\n")
                f.write(f"use_mub {bool(p['use_muB'])}\n")
                f.write(f"use_mus {bool(p['use_muS'])}\n")
                f.write(f"use_muq {bool(p['use_muQ'])}\n")
                f.write(f"samples {p['samples']}\n")
                f.write(f"sampling_method {p['sampling_method']}\n")
                f.write(f"force_temperature {bool(p['force_temperature'])}\n")
                f.write(f"temperature {p['temperature']}\n")
                f.write(f"delta_f_shear {bool(p['delta_f_shear'])}\n")
                f.write(f"delta_f_diffusion {bool(p.get('delta_f_diffusion', False))}\n")
                f.write(f"delta_f_bulk {bool(p.get('delta_f_bulk', False)) }\n")
                f.write(f"normalize_deltaf {bool(p.get('normalize_deltaf', False))}\n")
                f.write(f"y_max {p['y_max']}\n")
                f.write(f"seed {seed}\n")
                f.write(f"input_file {p['input_file']}\n")
                f.write(f"output_file {p['output_file']}\n")
                f.write(f"tables_path {p['tables_path']}\n")

        # Write to tmpdir (used by the run) and also save a copy to output/configs
        _write_cfg(run_cfg_file)
        _write_cfg(saved_cfg_file)

        return run_cfg_file
