import warnings
import os
import shutil
import subprocess
import re
import pandas as pd
import random
import numpy as np
from utils.db import insert_initial_condition
from stages.initial_condition import InitialCondition


# ---------------------------------------------------------------------------
# Standalone sparse-file utilities (importable without the wrapper class)
# ---------------------------------------------------------------------------

def read_sparse_trento_file(path: str) -> dict:
    """Read a sparse TRENTo output file (ic*.dat, TA*.dat, or TB*.dat).

    Header format (line 1):
        event_num  dxy  mult  xmin  ymin

    Data lines:
        x  y  value   (only non-zero cells are listed)

    Returns a dict with keys:
        dxy, mult, xmin, ymin, n_steps, grid (2-D numpy array, shape [n_steps, n_steps])

    The grid is indexed as grid[ix, iy] where:
        x = xmin + ix * dxy
        y = ymin + iy * dxy
    """
    with open(path, 'r') as f:
        lines = f.readlines()

    if not lines:
        raise RuntimeError(f"Empty file: {path}")

    # Parse header
    header = lines[0].split()
    dxy  = float(header[1])
    mult = float(header[2])
    xmin = float(header[3])
    ymin = float(header[4])

    # Grid runs from xmin to -xmin (symmetric), step dxy
    # n_steps = round(2*|xmin| / dxy) + 1, matching Trento's write_sparse_file
    xmax   = -xmin
    n_steps = int(round(2.0 * xmax / dxy)) + 1

    grid = np.zeros((n_steps, n_steps), dtype=np.float64)

    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        x, y, val = float(parts[0]), float(parts[1]), float(parts[2])
        ix = int(round((x - xmin) / dxy))
        iy = int(round((y - ymin) / dxy))
        if 0 <= ix < n_steps and 0 <= iy < n_steps:
            grid[ix, iy] = val

    return {
        'dxy':    dxy,
        'mult':   mult,
        'xmin':   xmin,
        'ymin':   ymin,
        'n_steps': n_steps,
        'grid':   grid,
    }


def read_ncoll_list_file(ncoll_list_path: str) -> np.ndarray:
    """Read the binary-collision position list file ``ncoll_list{n}.dat`` written
    by the TRENTo C++ binary (requires ``ncoll = true``).

    Each line contains the transverse midpoint ``x y`` of one binary collision
    (average of the two participant nucleon positions).

    Parameters
    ----------
    ncoll_list_path : str
        Path to the ncoll_list{n}.dat file.

    Returns
    -------
    numpy array of shape (Ncoll, 2), columns [x, y] in fm.
    Returns an empty (0, 2) array if no collisions are found.
    """
    points = []
    with open(ncoll_list_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                points.append((float(parts[0]), float(parts[1])))
    return np.array(points, dtype=np.float64).reshape(-1, 2)


def save_sparse_trento_file(path: str, grid_dict: dict, event_num: int = 0,
                             threshold: float = 0.0) -> None:
    """Write a dense numpy grid to TRENTo sparse format.

    Parameters
    ----------
    path       : output file path
    grid_dict  : dict as returned by ``read_sparse_trento_file`` or ``compute_ncoll_grid``
    event_num  : event number written in the header (default 0)
    threshold  : cells with value <= threshold are skipped (default 0)
    """
    dxy    = grid_dict['dxy']
    xmin   = grid_dict['xmin']
    ymin   = grid_dict['ymin']
    grid   = grid_dict['grid']
    mult   = float(grid.sum() * dxy * dxy)  # proxy multiplicity

    with open(path, 'w') as f:
        f.write(f"{event_num} {dxy} {mult} {xmin} {ymin}\n")
        n = grid.shape[0]
        for ix in range(n):
            x = xmin + ix * dxy
            for iy in range(n):
                val = grid[ix, iy]
                if val > threshold:
                    y = ymin + iy * dxy
                    f.write(f"{x} {y} {val}\n")

class TrentoInitialCondition(InitialCondition):
    def validate(self):
        """Perform validation specific to TRENTo if it's enabled."""
        if self.config['input']['initial_conditions']['type'] != 'Trento':
            return  # Skip validation if TRENTo is not the active IC

        grid = self.config['global']['grid']
        if grid['x_max'] != grid['y_max']:
            warnings.warn("Grid x_max and y_max are different. Using x_max as default.")

        if grid['step_eta'] > 0:
            warnings.warn("step_eta is non-zero, but TRENTo is 2D, setting it to zero.")
            self.config['global']['grid']['step_eta'] = 0


        #check for entropy dict
        if self.config['input']['initial_conditions']['parameters']['entropy-dict-dir'] == 'default':
            #check if centrality min and max are positive
            if self.config['input']['initial_conditions']['parameters']['centrality-min'] > 0 or self.config['input']['initial_conditions']['parameters']['centrality-max'] > 0:
                #warn and then set them to negative to generate random centrality
                self.config['input']['initial_conditions']['parameters']['centrality-min'] = -1
                self.config['input']['initial_conditions']['parameters']['centrality-max'] = -10
                print("Warning: Centrality min and max are positive, but no entropy dict provided. Setting them to negative to generate random centrality.")
            else:
                self.config['input']['initial_conditions']['parameters']['entropy-dict-dir'] = os.path.join(self.config['global']['basedir'], 'misc', 'PbPb_5020_sigma0d30_3M.dat')
                print("Warning: No entropy dict provided, using default PbPb_5020_sigma0d30_3M.dat.")
                

        print("Base validation for TRENTo completed.")

    def generate_seed(self):
        """Check if a seed is provided; if set to random, generate a random seed."""
        if self.config['input']['initial_conditions']['parameters']['seed'] == 'random':
            seed = random.randint(0, 2**31 - 1)
            print(f"Generated random seed for TRENTo: {seed}")
        else:
            seed = self.config['input']['initial_conditions']['parameters']['seed']
            print(f"Using provided seed for TRENTo: {seed}")
        return seed

    def create_temp_config(self, seed,event_id):
        """Create a temporary TRENTo configuration file using the YAML-provided parameters."""
        if self.config['input']['initial_conditions']['type'] != 'Trento':
            raise ValueError("create_temp_config should only be called when TRENTo is the active IC.")

        params = self.config['input']['initial_conditions']['parameters']
        #outputdir + event_(event_id) + /trento, sum the strings 
        output_dir = os.path.join(self.config['global']['output'], "event_" + str(event_id), 'trento')
        os.makedirs(output_dir, exist_ok=True)

        #check for freeestreaming
        if self.config['input'].get('preequilibrium', {}).get('type') == 'freestreaming':
            output_dir = os.path.join(self.config['global']['output'], "event_" + str(event_id), 'trento', 'ic.hdf')

        config_dir = os.path.join(self.config['global']['output'], "event_" + str(event_id), 'configs')
        os.makedirs(config_dir, exist_ok=True)

        

        config_file_path = os.path.join(config_dir, 'trento_config.dat')

        with open(config_file_path, 'w') as f:
            f.write(f"random-seed = {seed}\n")
            f.write(f"projectile = {params['ion_A']['species']}\n")
            f.write(f"projectile = {params['ion_B']['species']}\n")  # Fixed duplicate "projectile"
            f.write(f"number-events = {params['number-events']}\n")
            f.write(f"entropy-dict-dir = {params['entropy-dict-dir']}\n")
            f.write(f"output = {output_dir}\n")
            f.write(f"quiet = {str(params['quiet']).lower()}\n")
            f.write(f"no-header = {str(params['no-header']).lower()}\n")
            f.write(f"ncoll = {str(params['ncoll']).lower()}\n")
            f.write(f"sparse-output = {str(params['sparse-output']).lower()}\n")
            f.write(f"output-format = {str(params['output-format']).lower()}\n")
            f.write(f"reduced-thickness = {params['reduced-thickness']}\n")
            f.write(f"fluctuation = {params['fluctuation']}\n")
            f.write(f"fluctuation-type = {params['fluctuation-type']}\n")
            f.write(f"nucleon-width = {params['nucleon-width']}\n")
            f.write(f"nucleon-width-probability = {params['nucleon-width-probability']}\n")
            f.write(f"constit-width = {params['constit-width']}\n")
            f.write(f"constit-number = {params['constit-number']}\n")
            f.write(f"nucleon-min-dist = {params['nucleon-min-dist']}\n")
            f.write(f"number-nucleons = {params['number-nucleons']}\n")
            f.write(f"woods-saxon-radius = {params['woods-saxon-radius']}\n")
            f.write(f"woods-saxon-thickness = {params['woods-saxon-thickness']}\n")
            f.write(f"woods-saxon-omega = {params['woods-saxon-omega']}\n")
            f.write(f"beta2 = {params['beta2']}\n")
            f.write(f"beta3 = {params['beta3']}\n")
            f.write(f"beta4 = {params['beta4']}\n")
            f.write(f"cross-section = {params['cross-section']}\n")
            f.write(f"normalization = {params['normalization']}\n")
            f.write(f"b-min = {params['b-min']}\n")
            f.write(f"b-max = {params['b-max']}\n")
            f.write(f"centrality-min = {params['centrality-min']}\n")
            f.write(f"centrality-max = {params['centrality-max']}\n")
            f.write(f"grid-max = {self.config['global']['grid']['x_max']}\n")
            f.write(f"grid-step = {self.config['global']['grid']['step_x']}\n")
            # f.write(f"reduced-thickness-form = {params['reduced-thickness-form']}\n")

        print(f"TRENTo config file created at {config_file_path}")
        return config_file_path

    def run(self, event_id):
        """Run the TRENTo IC generator and insert results into the database."""
        if self.config['input']['initial_conditions']['type'] != 'Trento':
            print("Skipping TRENTo execution because it is not the active initial condition.")
            return

        seed = self.generate_seed()
        config_file_path = self.create_temp_config(seed, event_id)
        tmp_trento_dir = os.path.join(self.config['global']['tmp'], "event_" + str(event_id), 'trento')
        output_file = os.path.join(os.path.dirname(tmp_trento_dir), f'trento_output_{event_id}.txt')

        ## Run TRENTo
        # trento executable from basedir
        trento_executable = self.config['global']['basedir'] + '/models/trento/build/src/trento'
        command = f"{trento_executable} -c {config_file_path} > {output_file}"
        print(f"Running: {command}")
        os.system(command)

        # Parse the output and insert results into the database
        events_data = self.parse_output(output_file)
        if events_data:
            event_data = events_data[0]  # Assume one event per execution
            insert_initial_condition(
                self.db_connection,
                event_id=event_id,
                seed=seed,
                seed2=None,
                ic_type='trento'
            )
            self.centrality_estimator = event_data['s']/self.config['input']['initial_conditions']['parameters']['normalization']


        #convert to ccake format
        ccake_ic_path = os.path.join(self.config['global']['output'], "event_" + str(event_id), 'trento', f'ccake_ic.dat')
        sparse_output = False
        #check for freestreaming
        if self.config['input'].get('preequilibrium', {}).get('type') != 'freestreaming':
            if self.config['input']['initial_conditions']['parameters']['sparse-output'] == True:
                sparse_output = True
                trento_ic_path = os.path.join(self.config['global']['output'], "event_" + str(event_id), 'trento', f'ic0.dat')

            else:
                trento_ic_path = os.path.join(self.config['global']['output'], "event_" + str(event_id), 'trento', f'0.dat')
            self.convert_to_ccake( trento_ic_path,ccake_ic_path, sparse_output)

        # When ncoll = true, TRENTo writes ncoll_list{n}.dat with the (x,y)
        # midpoints of each binary collision.  Log the count as a sanity check.
        ncoll_enabled = self.config['input']['initial_conditions']['parameters'].get('ncoll', False)
        if ncoll_enabled:
            try:
                self.read_ncoll_list(event_id, event_num=0)
            except FileNotFoundError as exc:
                print(f"[ncoll] Warning: {exc}")

        # persist the CCAKE-format initial condition to the top-level output dir
        # so it survives end-of-run cleanup. Controlled by the per-stage
        # 'keep_result' flag.
        keep_result = self.config['input']['initial_conditions']['parameters'].get('keep_result', False)
        if keep_result and os.path.exists(ccake_ic_path):
            dest = os.path.join(self.config['global']['output'], f"ccake_ic_{event_id}.dat")
            shutil.copy2(ccake_ic_path, dest)
            print(f"Persisted initial condition to {dest}")

    def parse_output(self, output_file):
        """Parse the output file to extract entropy and eccentricity information."""
        with open(output_file, 'r') as f:
            lines = f.readlines()

        events_data = []
        ncoll_enabled = self.config['input']['initial_conditions']['parameters'].get('ncoll', False)

        for line in lines:
            fields = re.split(r'\s+', line.strip())
            if len(fields) < 8 or not fields[0].isdigit():
                continue

            try:
                if ncoll_enabled and len(fields) == 9:
                    event = {
                        'ev': int(fields[0]),
                        'b': float(fields[1]),
                        'Npart': int(fields[2]),
                        'Ncoll': int(fields[3]),
                        's': float(fields[4]),
                        'e2': float(fields[5]),
                        'e3': float(fields[6]),
                        'e4': float(fields[7]),
                        'e5': float(fields[8])
                    }
                    events_data.append(event)
                elif not ncoll_enabled and len(fields) == 8:
                    event = {
                        'ev': int(fields[0]),
                        'b': float(fields[1]),
                        'Npart': int(fields[2]),
                        's': float(fields[3]),
                        'e2': float(fields[4]),
                        'e3': float(fields[5]),
                        'e4': float(fields[6]),
                        'e5': float(fields[7])
                    }
                    events_data.append(event)
                self.centrality_estimator = event['s']
            except ValueError:
                continue

        return events_data
    

    # ------------------------------------------------------------------
    # Binary-collision density helpers
    # ------------------------------------------------------------------

    def read_ncoll_list(self, event_id: int, event_num: int = 0) -> np.ndarray:
        """Read the binary-collision position list from ``ncoll_list{event_num}.dat``.

        TRENTo writes this file when ``ncoll = true``.  Each line is the
        transverse midpoint (x, y) of one colliding nucleon pair.

        Parameters
        ----------
        event_id  : pipeline event identifier (used to locate the output directory)
        event_num : TRENTo event index within that run (default 0 for single-event runs)

        Returns
        -------
        numpy array of shape (Ncoll, 2), columns [x, y] in fm.
        """
        trento_dir = os.path.join(
            self.config['global']['output'], f"event_{event_id}", 'trento'
        )
        ncoll_path = os.path.join(trento_dir, f'ncoll_list{event_num}.dat')

        if not os.path.isfile(ncoll_path):
            raise FileNotFoundError(
                f"ncoll_list{event_num}.dat not found at {ncoll_path}. "
                "Make sure ncoll = true in the TRENTo config."
            )

        positions = read_ncoll_list_file(ncoll_path)
        print(f"[ncoll] event {event_id} (TRENTo #{event_num}): Ncoll = {len(positions)}")
        return positions

    def convert_to_ccake(self, input_file, output_file, sparse_output):
        """Convert the TRENTo output to CCAKE input format."""
        stepx = self.config['global']['grid']['step_x']
        stepy = stepx  # Assuming same step size in x and y
        stepEta = 0.1
        xmax = self.config['global']['grid']['x_max']
        xmin = -xmax
        ymin = -xmax
        etamin = -0.5


        with open(input_file, 'r') as infile:
            lines = infile.readlines()

        with open(output_file, 'w') as outfile:
            outfile.write(f"#0 {stepx} {stepy} {stepEta} 0 {xmin} {ymin} {etamin}\n")

            if sparse_output:
                # Parse sparse output: expect (x, y, eps) format
                for line in lines[1:]:  # Skip header
                    if line.startswith("#"):
                        continue
                    try:
                        x, y, eps = map(float, line.split())
                        outfile.write(f"{x} {y} 0 {eps} 0 0 0 0 0 0 0 0 0 0 0 0 0\n")
                    except ValueError:
                        continue
            else:
                # Parse dense grid
                for ix, line in enumerate(lines):
                    if line.startswith("#"):
                        continue
                    x = xmin + ix * stepx
                    eps_values = line.split()
                    for iy, eps in enumerate(eps_values):
                        y = ymin + iy * stepy
                        outfile.write(f"{x} {y} 0 {eps} 0 0 0 0 0 0 0 0 0 0 0 0 0\n")
