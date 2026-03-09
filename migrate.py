import json
import os
from database import save_ranking_data, save_roles_data, save_status_meta, save_vc_lb_meta, save_vc_points

# Load and migrate ranking_data.json
if os.path.exists("ranking_data.json"):
    with open("ranking_data.json", "r") as f:
        ranking_data = json.load(f)
    save_ranking_data(ranking_data)
    print("Migrated ranking_data.json")

# Load and migrate roles_menus.json
if os.path.exists("roles_menus.json"):
    with open("roles_menus.json", "r") as f:
        roles_data = json.load(f)
    save_roles_data(roles_data)
    print("Migrated roles_menus.json")

# Load and migrate status_meta.json
if os.path.exists("status_meta.json"):
    with open("status_meta.json", "r") as f:
        status_data = json.load(f)
    save_status_meta(status_data)
    print("Migrated status_meta.json")

# Load and migrate vc_lb_meta.json
if os.path.exists("vc_lb_meta.json"):
    with open("vc_lb_meta.json", "r") as f:
        vc_lb_data = json.load(f)
    save_vc_lb_meta(vc_lb_data)
    print("Migrated vc_lb_meta.json")

# Load and migrate vc_points.json
if os.path.exists("vc_points.json"):
    with open("vc_points.json", "r") as f:
        vc_points_data = json.load(f)
    save_vc_points(vc_points_data)
    print("Migrated vc_points.json")

print("Migration complete!")