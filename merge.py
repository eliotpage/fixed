import json

# Load the files
with open('drawings.json', 'r') as f:
    drawings = json.load(f)

with open('shared.json', 'r') as f:
    shared = json.load(f)

# Build dicts keyed by _id for easy lookup
def build_dict(features):
    return {f['properties']['_id']: f for f in features}

drawings_dict = build_dict(drawings)
shared_dict = build_dict(shared)

# Start merging
merged_dict = {}

all_ids = set(drawings_dict.keys()) | set(shared_dict.keys())

for _id in all_ids:
    d_feat = drawings_dict.get(_id)
    s_feat = shared_dict.get(_id)
    
    # Case 1: both deleted = true → skip entirely
    if d_feat and s_feat and d_feat['properties'].get('deleted') and s_feat['properties'].get('deleted'):
        continue

    # Case 2: only in one file → keep it
    if d_feat and not s_feat:
        merged_dict[_id] = d_feat
        continue
    if s_feat and not d_feat:
        merged_dict[_id] = s_feat
        continue

    # Case 3: in both, handle deletion flags
    merged = d_feat.copy()
    merged_props = merged['properties'].copy()
    
    if d_feat['properties'].get('deleted') or s_feat['properties'].get('deleted'):
        merged_props['deleted'] = True
    merged['properties'] = merged_props

    # You could also choose which geometry to keep; here we take `d_feat` geometry
    merged_dict[_id] = merged

# Convert dict back to list
merged_list = list(merged_dict.values())

# Save merged file
with open('merged_drawings.json', 'w') as f:
    json.dump(merged_list, f, indent=2)

print(f"Merged {len(drawings)} + {len(shared)} → {len(merged_list)} features saved to merged_drawings.json")