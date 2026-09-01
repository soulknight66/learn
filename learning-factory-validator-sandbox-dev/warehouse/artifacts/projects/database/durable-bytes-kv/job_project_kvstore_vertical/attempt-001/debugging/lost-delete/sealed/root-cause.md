# Root cause

`_apply` handles set records but turns delete records into no-ops. Live deletion mutates the
dictionary directly, hiding the defect until replay. There is exactly one intentional defect.
