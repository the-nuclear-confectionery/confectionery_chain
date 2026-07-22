// Sample back-to-back dijets from AMPT events.
// Compile: g++ -std=c++17 sample_dijets.cpp -o sample_dijets \
//   -I$PYTHIA8/include -L$PYTHIA8/lib -lpythia8 -lm

#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <unordered_map>
#include <algorithm>
#include <cmath>
#include <random>
#include <iomanip>
#include "Pythia8/Pythia.h"

using namespace std;
using namespace Pythia8;

// Cartesian production vertex (lab frame).
struct Vertex { double x, y, z, t; };

// ─── Config: INI → "section.key" → value ─────────────────────────────────────

static void trim(string& s) {
    size_t a = s.find_first_not_of(" \t\r\n");
    size_t b = s.find_last_not_of(" \t\r\n");
    s = (a == string::npos) ? "" : s.substr(a, b - a + 1);
}

unordered_map<string, string> read_config(const string& path) {
    ifstream file(path);
    if (!file) { cerr << "Error: cannot open " << path << "\n"; exit(1); }

    unordered_map<string, string> cfg;
    string line, section;
    while (getline(file, line)) {
        trim(line);
        if (line.empty() || line[0] == '#' || line[0] == ';') continue;
        if (line[0] == '[') { section = line.substr(1, line.find(']') - 1); continue; }
        size_t eq = line.find('=');
        if (eq == string::npos) continue;
        string key = line.substr(0, eq), val = line.substr(eq + 1);
        trim(key); trim(val);
        cfg[section + "." + key] = val;
    }
    return cfg;
}

string get(const unordered_map<string, string>& cfg, const string& key) {
    auto it = cfg.find(key);
    if (it == cfg.end()) { cerr << "Error: missing config key: " << key << "\n"; exit(1); }
    return it->second;
}

// ─── AMPT vertex parsers ─────────────────────────────────────────────────────

vector<Vertex> parse_binary_collisions(const string& path, double sqrts) {
    ifstream file(path);
    if (!file) { cerr << "Error: cannot open " << path << "\n"; exit(1); }

    const double mp = 0.938;
    const double gamma = sqrts / (2.0 * mp);
    const double v_beam = sqrt(1.0 - 1.0 / (gamma * gamma));

    vector<double> xc, yc, zp, zt;
    string line;
    while (getline(file, line)) {
        istringstream iss(line);
        int jp, jt; double x, y, zP, zT;
        if (!(iss >> jp >> jt >> x >> y >> zP >> zT)) continue;
        xc.push_back(x); yc.push_back(y);
        zp.push_back(zP); zt.push_back(zT);
    }
    if (xc.empty()) { cerr << "Error: no binary collisions in " << path << "\n"; exit(1); }

    double z_P_max = *max_element(zp.begin(), zp.end());
    double z_T_max = *max_element(zt.begin(), zt.end());

    vector<Vertex> v;
    v.reserve(xc.size());
    for (size_t i = 0; i < xc.size(); ++i) {
        double z_P_lab = (zp[i] - z_P_max) / gamma;
        double z_T_lab = (z_T_max - zt[i]) / gamma;
        v.push_back({xc[i], yc[i],
                     0.5 * (z_P_lab + z_T_lab),
                     (z_T_lab - z_P_lab) / (2.0 * v_beam)});
    }
    cout << "[info] loaded " << v.size() << " binary collisions\n";
    return v;
}

vector<Vertex> parse_minijets(const string& path) {
    ifstream file(path);
    if (!file) { cerr << "Error: cannot open " << path << "\n"; exit(1); }

    vector<Vertex> v;
    string line;
    getline(file, line); // event header
    while (getline(file, line)) {
        istringstream iss(line);
        int pid, status; double px, py, pz, mass, x, y, z, t;
        if (!(iss >> pid >> px >> py >> pz >> mass >> x >> y >> z >> t >> status)) continue;
        v.push_back({x, y, z, 0.0});
    }
    cout << "[info] loaded " << v.size() << " minijets\n";
    return v;
}

// TRENTo binary-collision list (ncoll_list{n}.dat, written when ncoll = true).
// Each line is the transverse midpoint "x y" of one binary collision. TRENTo is
// boost-invariant, so the hard process is placed at z = t = 0 (mid-rapidity);
// the free-streamer then carries the partons out to tau_hydro. No sqrt(s) boost
// is needed because there is no longitudinal production information to unfold.
vector<Vertex> parse_trento_ncoll(const string& path) {
    ifstream file(path);
    if (!file) { cerr << "Error: cannot open " << path << "\n"; exit(1); }

    vector<Vertex> v;
    string line;
    while (getline(file, line)) {
        istringstream iss(line);
        double x, y;
        if (!(iss >> x >> y)) continue;
        v.push_back({x, y, 0.0, 0.0});
    }
    if (v.empty()) { cerr << "Error: no binary collisions in " << path << "\n"; exit(1); }
    cout << "[info] loaded " << v.size() << " TRENTo binary collisions\n";
    return v;
}

// Free-stream a parton from production vertex `v` (lab) to Milne proper time tau_f.
// Velocity v = p/E (exact for massless; excellent approx for hard partons).
// Returns Milne endpoint (x, y, eta_s, tau=tau_f); sets late=true if already past tau_f.
struct FSResult {
    double x, y, eta_s, tau;
    bool late;
};

FSResult free_streamer(const Vertex& v, double px, double py, double pz, double E, double tau_f) {
    double vx = px / E, vy = py / E, vz = pz / E;
    // z back-propagated to t = 0
    double pos_init = v.z - vz * v.t;

    double tau_prod = sqrt(max(0.0, v.t*v.t - v.z*v.z));
    if (tau_prod >= tau_f) return { v.x, v.y,
        (v.t > fabs(v.z)) ? 0.5*log((v.t + v.z)/(v.t - v.z)) : 0.0,
        tau_prod, true };

    double Delta = sqrt(pos_init*pos_init + tau_f*tau_f * (1.0 - vz*vz));
    double tf = (vz * pos_init + Delta) / (1.0 - vz*vz);
    double xf = v.x + vx * (tf - v.t);
    double yf = v.y + vy * (tf - v.t);
    double zf = v.z + vz * (tf - v.t);
    double eta_s = (tf > fabs(zf)) ? 0.5*log((tf + zf)/(tf - zf)) : 0.0;
    return { xf, yf, eta_s, tau_f, false };
}

// ─── Main ────────────────────────────────────────────────────────────────────

int main(int argc, char* argv[]) {
    if (argc != 2) { cerr << "Usage: " << argv[0] << " <config_file>\n"; return 1; }

    auto cfg = read_config(argv[1]);
    string ampt_dir      = get(cfg, "input.ampt_dir");
    string vertex_source = get(cfg, "input.vertex_source");
    double sqrts         = stod(get(cfg, "pythia.sqrts"));
    double pt_min        = stod(get(cfg, "pythia.pt_min"));
    double pt_max        = stod(get(cfg, "pythia.pt_max"));
    int    n_dijets      = stoi(get(cfg, "sampling.n_dijets"));
    string csv_file      = get(cfg, "output.csv_file");
    // tau_hydro = 0 → output production point; > 0 → free-stream to that Milne proper time (fm/c)
    double tau_hydro     = cfg.count("output.tau_hydro") ? stod(cfg.at("output.tau_hydro")) : 0.0;

    cout << "[info] sqrt(s_NN) = " << sqrts << " GeV, source = " << vertex_source
         << ", N = " << n_dijets << ", pT in [" << pt_min << ", " << pt_max << "]\n";
    cout << "[info] Milne output; "
         << (tau_hydro > 0 ? "free-stream to tau = " + to_string(tau_hydro) + " fm/c"
                           : "production point (no free-streaming)")
         << "\n";

    auto find_file = [&](const string& rel_ana, const string& rel_direct) -> string {
        string p1 = ampt_dir + "/ana/" + rel_ana;
        string p2 = ampt_dir + "/" + rel_direct;
        if (ifstream(p1)) return p1;
        if (ifstream(p2)) return p2;
        cerr << "Error: cannot find " << rel_ana << " in " << ampt_dir << "/ana/ or " << ampt_dir << "/\n";
        exit(1);
    };

    vector<Vertex> vertices;
    if (vertex_source == "binary")
        vertices = parse_binary_collisions(find_file("binary-collisions.dat", "binary-collisions.dat"), sqrts);
    else if (vertex_source == "minijet")
        vertices = parse_minijets(find_file("minijet-initial-beforePropagation.dat", "minijet-initial-beforePropagation.dat"));
    else if (vertex_source == "trento")
        // TRENTo single-event runs write ncoll_list0.dat into the trento output dir.
        vertices = parse_trento_ncoll(find_file("ncoll_list0.dat", "ncoll_list0.dat"));
    else { cerr << "Error: unknown vertex_source: " << vertex_source << "\n"; return 1; }

    Pythia pythia;
    pythia.readString("HardQCD:all = on");
    pythia.readString("PartonLevel:ISR = off");
    pythia.readString("PartonLevel:FSR = off");
    pythia.readString("PartonLevel:MPI = off");
    pythia.readString("HadronLevel:all = off");
    pythia.readString("Beams:idA = 2212");
    pythia.readString("Beams:idB = 2212");
    pythia.readString("Beams:eCM = " + to_string(sqrts));
    pythia.readString("PhaseSpace:pTHatMin = " + to_string(pt_min));
    pythia.readString("PhaseSpace:pTHatMax = " + to_string(pt_max));
    // seed=0 → PYTHIA uses current time (non-reproducible)
    pythia.readString("Random:setSeed = on");
    pythia.readString("Random:seed = 0");
    pythia.readString("Print:quiet = on");
    if (!pythia.init()) { cerr << "PYTHIA initialization failed\n"; return 1; }

    // true hardware entropy for vertex sampling
    random_device rd;
    mt19937 rng(rd());
    uniform_int_distribution<> pick(0, (int)vertices.size() - 1);

    ofstream csv(csv_file);
    // p0..p3: covariant 4-momentum in Milne coords (tau,x,y,eta_s), metric diag(+1,-1,-1,-tau^2)
    // p0 = E cosh(eta_s) - pz sinh(eta_s)  [= mT for massless parton from origin]
    // p1 = px, p2 = py
    // p3 = tau*(E sinh(eta_s) - pz cosh(eta_s))  [= 0 for massless parton from origin]
    csv << "dijet_id,parton_idx,pid,mass,x_vtx,y_vtx,eta_s,tau,p0,p1,p2,p3,pT,phi,y,eta\n";
    csv << fixed << setprecision(8);

    int n_done = 0, n_late = 0, max_attempts = max(100, 50 * n_dijets), n_attempts = 0;
    while (n_done < n_dijets) {
        if (++n_attempts > max_attempts) {
            cerr << "Error: only " << n_done << "/" << n_dijets
                 << " dijets after " << n_attempts << " attempts\n"; return 1;
        }
        if (!pythia.next()) continue;

        vector<int> hard;
        for (int i = 0; i < pythia.event.size(); ++i)
            if (abs(pythia.event[i].status()) == 23) hard.push_back(i);
        if (hard.size() != 2) continue;

        Vertex v_prod = vertices[pick(rng)];
        for (int k = 0; k < 2; ++k) {
            const auto& p = pythia.event[hard[k]];
            double px = p.px(), py = p.py(), pz = p.pz(), E = p.e();
            double pT   = sqrt(px*px + py*py);
            double phi  = atan2(py, px);
            double pmag = sqrt(px*px + py*py + pz*pz);
            double yr   = (E    != fabs(pz)) ? 0.5*log((E    + pz)/(E    - pz)) : 0.0;
            double eta  = (pmag != fabs(pz)) ? 0.5*log((pmag + pz)/(pmag - pz)) : 0.0;

            FSResult fs;
            if (tau_hydro > 0) {
                fs = free_streamer(v_prod, px, py, pz, E, tau_hydro);
                if (fs.late) ++n_late;
            } else {
                double tau_p  = sqrt(max(0.0, v_prod.t*v_prod.t - v_prod.z*v_prod.z));
                double etas_p = (v_prod.t > fabs(v_prod.z))
                              ? 0.5*log((v_prod.t + v_prod.z)/(v_prod.t - v_prod.z)) : 0.0;
                fs = { v_prod.x, v_prod.y, etas_p, tau_p, false };
            }

            double p0 = E * cosh(fs.eta_s) - pz * sinh(fs.eta_s);
            double p3 = fs.tau * (E * sinh(fs.eta_s) - pz * cosh(fs.eta_s));

            csv << n_done << "," << k << "," << p.id() << "," << p.m() << ","
                << fs.x << "," << fs.y << "," << fs.eta_s << "," << fs.tau << ","
                << p0 << "," << px << "," << py << "," << p3 << ","
                << pT << "," << phi << "," << yr << "," << eta << "\n";
        }
        ++n_done;
    }

    if (n_late > 0)
        cout << "[warn] " << n_late << " parton(s) born after tau_hydro (kept production point)\n";
    cout << "[info] wrote " << n_done << " dijets (" << 2*n_done
         << " partons) to " << csv_file << "\n";
    return 0;
}
