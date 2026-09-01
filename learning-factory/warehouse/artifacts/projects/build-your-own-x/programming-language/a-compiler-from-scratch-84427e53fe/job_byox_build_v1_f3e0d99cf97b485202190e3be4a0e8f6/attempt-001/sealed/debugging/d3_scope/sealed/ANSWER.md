# D3 answer

Use a stack of maps and remove exactly the map pushed for the block, ideally with `ensure`. A declaration modifies only the top map. Resolution scans maps from inner to outer and returns the first match. Never delete a name from an outer map when leaving an inner scope, and never keep the inner map after exit. Monotonic slot allocation avoids reusing the outer slot accidentally.
