from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd

root=Path(__file__).resolve().parent/"synthetic_step4"
rng=np.random.default_rng(4)
for age, base in [("P10", 1000), ("P20", 2000), ("P50", 3000)]:
    for k in range(3):
        cid=f"SYN{k+1}_{age}"
        d=root/"cells"/cid; d.mkdir(parents=True, exist_ok=True)
        rin=700-base/20+rng.normal(0,20); tau=18+base/500+rng.normal(0,1)
        summary={"cell_id":cid,"age_group":age,"n_segments":20+k,"total_cable_length_um":base+k*20,"maximum_branch_order":4+k,"n_terminals":6+k,"input_resistance_MOhm":rin,"tau_ms":tau,"tau_fit_r2":0.99,"maximum_path_distance_um":120+k*10,"mean_soma_normalised_attenuation":0.72,"minimum_soma_normalised_attenuation":0.45,"resting_stable":True,"matrix_mode":"representative","n_transfer_rows":81}
        (d/"manifest.json").write_text(json.dumps({"status":"complete"}))
        (d/f"{cid}_passive_summary.json").write_text(json.dumps(summary))
        (d/f"{cid}_structural_validation.json").write_text(json.dumps({"ready_for_simulation":True}))
        (d/f"{cid}_resting_test.json").write_text(json.dumps({"stable_at_rest":True}))
        (d/f"{cid}_current_step_summary.json").write_text(json.dumps({"soma":{}}))
        t=np.linspace(0,130,300); v=-70-2*(1-np.exp(-np.maximum(t-20,0)/tau)); pd.DataFrame({"time_ms":t,"soma_mV":v}).to_csv(d/f"{cid}_soma_trace.csv",index=False)
        dist=np.linspace(5,150,20); pd.DataFrame({"segment_id":range(20),"tree":1,"order":np.arange(20)%5,"terminal_type":"none","path_distance_um":dist,"radial_distance_um":dist*.7,"baseline_mV":-70,"steady_mV":-72,"delta_v_mV":-2*np.exp(-dist/220),"soma_normalised_attenuation":np.exp(-dist/220)}).to_csv(d/f"{cid}_attenuation_map.csv",index=False)
        pd.DataFrame({"source_segment_id":[None],"target_segment_id":[1],"transfer_impedance_MOhm":[120]}).to_csv(d/f"{cid}_bidirectional_transfer.csv",index=False)
        pd.DataFrame({"source_segment_id":[None],"target_segment_id":[None],"transfer_impedance_MOhm":[rin]}).to_csv(d/f"{cid}_transfer_matrix.csv",index=False)
print(root)
