import os
import subprocess
import sys


def test_settings_limita_hilos_de_torch():
    env = {k: v for k, v in os.environ.items() if k != "OMP_NUM_THREADS"}
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    out = subprocess.run(
        [sys.executable, "-c",
         "import django; django.setup(); import torch; print(torch.get_num_threads())"],
        env=env, capture_output=True, text=True, check=True).stdout.split()[-1]
    assert out == "2"
