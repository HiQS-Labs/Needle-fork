#!/bin/bash
# GH-5 P4-lite: build the QAT adapter into a .cact and score THE DEPLOYED ARTIFACT.
#   spike/mlx/post_train_qat.sh            # build + eval, print the verdict
#   spike/mlx/post_train_qat.sh --wire     # ...and point the hook at it (data/oracle/config.json)
set -euo pipefail
cd "/Users/noelsaw/Documents/GitHub Repos/Needle-fork"
export HF_HUB_DISABLE_XET=1 NEEDLE_TELEMETRY=0
PY=.venv-mlx-spike/bin/python
ADAPTER=data/spike-mlx/mlx-lora-10k-qat.pkl
CACT=data/spike-mlx/oracle-10k-qat.cact
L=data/spike-mlx/logs

echo "=== 1. training receipt ==="
$PY -c "import json;d=json.load(open('$L/p3-10k-qat-receipt.json'));print({k:d[k] for k in ('numerics','steps_run','final_loss','final_val_loss','median_s_per_step','peak_gb')})"

echo; echo "=== 2. needle build -- the adapter declares qat_bits_map, so the mixed scheme is picked and no --bits override is needed ==="
$PY -c "import pickle;d=pickle.load(open('$ADAPTER','rb'));print('adapter declares:',d['qat_bits_map'],'|',d['trained_numerics'])"
.venv-mlx-spike/bin/needle build checkpoints/needle2.pkl --lora "$ADAPTER" --out "$CACT" | grep -E "scheme|wrote"

echo; echo "=== 3. score the DEPLOYED artifact: native engine, same 200 rows (seed 0) as every other column ==="
$PY utils/hooks/eval_cact.py --cact "$CACT" --rows 200 --seed 0 --receipt "$L/eval-cact-10k-qat.json"

echo; echo "=== 4. the bars, same 200 rows ==="
echo "  static majority top-1        12.50%   (n=200 seed 0; 16.30% at n=1000)"
echo "  2k adapter, fp32 MLX ranking 22.00%   (the number the hook can NOT deliver)"
echo "  2k adapter, PTQ .cact         8-10%   (D7: destroyed by PTQ)"
echo "  -> shippable = precision-when-answering clearly above 12.50%, top-1 overall near the ranking number"

if [[ "${1:-}" == "--wire" ]]; then
  mkdir -p data/oracle
  $PY - <<PYEOF
import json, os
p = "data/oracle/config.json"
cfg = json.load(open(p)) if os.path.exists(p) else {}
cfg["cact"] = os.path.abspath("$CACT"); cfg["show"] = True
json.dump(cfg, open(p, "w"), indent=2); print("wired:", cfg["cact"])
PYEOF
  echo "now: $PY utils/hooks/oracle_install.py --apply   (dry-run first without --apply)"
fi
