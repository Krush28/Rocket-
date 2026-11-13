"""Shared-load matching with OR-Tools CP-SAT: assign pooled farmers' loads to vehicles minimising total cost.
Pool candidates are SIMULATED seed rows (labelled) until real farmer listings exist."""
import math
import random
import zlib

from ortools.sat.python import cp_model

from .demo_data import TRANSPORTERS
from .geo import road_km

SIM = "[Simulated]"


def simulated_pool(crop, dest_name, dest_ll, origin_ll, n=4, factor=1.3):
    """Nearby farmers heading to the same destination. Deterministic seed; clearly labelled simulated."""
    rng = random.Random(zlib.crc32(f"{crop}|{dest_name}|{round(origin_ll[0],1)}|{round(origin_ll[1],1)}".encode()))
    out = []
    for i in range(n):
        ll = (origin_ll[0] + rng.uniform(-0.15, 0.15), origin_ll[1] + rng.uniform(-0.15, 0.15))
        out.append(dict(id=f"S{i+1}", name=f"{SIM} Farmer {i+1}", qty_qtl=rng.choice([15, 20, 25, 30, 40]), ll=ll,
                        km=road_km(ll, dest_ll, factor), pickup_gap_km=round(road_km(ll, origin_ll, factor), 1)))
    return out


def match(user_qty, user_km, pool, max_pickup_gap_km=25, vehicles=None):
    """Returns per-farmer cost allocation and savings vs everyone shipping alone. Cost model per vehicle: base + per_km * (longest member route)."""
    vehicles = vehicles or [v for v in TRANSPORTERS if not v["refrigerated"]]
    members = [dict(id="YOU", name="You", qty_qtl=user_qty, km=user_km)] + [p for p in pool if p["pickup_gap_km"] <= max_pickup_gap_km]
    if len(members) == 1:
        return {"status": "no_match", "reason": "No compatible nearby loads."}

    def solo(m):
        return min(math.ceil(m["qty_qtl"] / v["capacity_qtl"]) * (v["base"] + v["per_km"] * m["km"]) for v in vehicles)
    solo_costs = {m["id"]: solo(m) for m in members}

    mdl = cp_model.CpModel()
    slots = [(vi, k) for vi, v in enumerate(vehicles) for k in range(len(members))]  # up to len(members) vehicles of each type
    x = {(f, s): mdl.NewBoolVar(f"x{f}_{s}") for f in range(len(members)) for s in range(len(slots))}
    y = {s: mdl.NewBoolVar(f"y{s}") for s in range(len(slots))}
    r = {s: mdl.NewIntVar(0, 2000, f"r{s}") for s in range(len(slots))}  # route km of vehicle slot
    for f, m in enumerate(members):
        mdl.Add(sum(x[f, s] for s in range(len(slots))) == 1)
    for s, (vi, _) in enumerate(slots):
        cap = int(vehicles[vi]["capacity_qtl"])
        mdl.Add(sum(int(m["qty_qtl"]) * x[f, s] for f, m in enumerate(members)) <= cap * y[s])
        for f, m in enumerate(members):
            mdl.Add(r[s] >= int(math.ceil(m["km"])) * x[f, s])
    cost = sum(int(vehicles[vi]["base"]) * y[s] + int(vehicles[vi]["per_km"]) * r[s] for s, (vi, _) in enumerate(slots))
    mdl.Minimize(cost)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    st = solver.Solve(mdl)
    if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {"status": "infeasible", "reason": "No feasible assignment (load too large for available vehicles?)."}
    total = solver.ObjectiveValue()
    vehicles_used, alloc = [], {m["id"]: 0.0 for m in members}
    for s, (vi, _) in enumerate(slots):
        if solver.Value(y[s]):
            idx = [f for f in range(len(members)) if solver.Value(x[f, s])]
            veh_cost = vehicles[vi]["base"] + vehicles[vi]["per_km"] * solver.Value(r[s])
            q_sum = sum(members[f]["qty_qtl"] for f in idx)
            for f in idx:
                alloc[members[f]["id"]] += veh_cost * members[f]["qty_qtl"] / q_sum  # split by quantity share
            vehicles_used.append(dict(vehicle=vehicles[vi]["vehicle"], cost=round(veh_cost), members=[members[f]["id"] for f in idx],
                                      load_qtl=q_sum, capacity_qtl=vehicles[vi]["capacity_qtl"]))
    solo_total = sum(solo_costs.values())
    you_solo, you_pool = solo_costs["YOU"], alloc["YOU"]
    return {"status": "ok", "label": "ESTIMATE", "simulated_members": True,
            "members": [dict(id=m["id"], name=m["name"], qty_qtl=m["qty_qtl"], pickup_gap_km=m.get("pickup_gap_km", 0),
                             solo_cost=round(solo_costs[m["id"]]), pooled_cost=round(alloc[m["id"]])) for m in members],
            "vehicles": vehicles_used, "total_pooled": round(total), "total_solo": round(solo_total),
            "you": dict(solo=round(you_solo), pooled=round(you_pool), saving=round(you_solo - you_pool),
                        saving_pct=round(100 * (you_solo - you_pool) / you_solo, 1) if you_solo else 0)}
