"""Multi-seed EEGNet replication: same three protocols, repeated over N random seeds, so the
deep-model rows can be reported as mean +/- sd instead of a single run.

Usage: eegnet_seeds.py <DEAP|DREAMER> <n_seeds> <device>
Writes ../results/eegnet_<dataset>.json
"""
import pickle, time, json, warnings, os, sys
from pathlib import Path
import numpy as np
import scipy.io as sio
import torch, torch.nn as nn
from sklearn.model_selection import StratifiedKFold, GroupKFold, LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")

FS, BASE_S, WIN_S, STEP_S, LAST_S = 128, 3, 4, 2, 60
HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("QEEG_DATA_ROOT", HERE / "../.."))
OUT = HERE / "../results"; OUT.mkdir(exist_ok=True)

WHICH = sys.argv[1] if len(sys.argv) > 1 else "DEAP"
NSEED = int(sys.argv[2]) if len(sys.argv) > 2 else 5
DEV = sys.argv[3] if len(sys.argv) > 3 else ("cuda:0" if torch.cuda.is_available() else "cpu")


def windows_from(sig):
    T = WIN_S * FS
    return np.stack([sig[:, st:st+T] for st in range(0, sig.shape[1]-T+1, STEP_S*FS)])


def load_deap():
    X, val, aro, subj, trial = [], [], [], [], []
    for sf in sorted((ROOT/"data/deap/data_preprocessed_python").glob("s*.dat")):
        s = int(sf.stem[1:]); dd = pickle.load(open(sf, "rb"), encoding="latin1")
        for t in range(dd["data"].shape[0]):
            w = windows_from(dd["data"][t, :32, BASE_S*FS:]); X.append(w)
            val += [dd["labels"][t, 0]]*len(w); aro += [dd["labels"][t, 1]]*len(w)
            subj += [s]*len(w); trial += [f"{s}_{t}"]*len(w)
    return np.concatenate(X).astype("float32"), np.array(val), np.array(aro), np.array(subj), np.array(trial)


def load_dreamer():
    X, val, aro, subj, trial = [], [], [], [], []
    D = sio.loadmat(ROOT/"DREAMER.mat", struct_as_record=False, squeeze_me=True)["DREAMER"]
    for si, s in enumerate(D.Data):
        sv, sa = np.array(s.ScoreValence), np.array(s.ScoreArousal)
        for t in range(len(s.EEG.stimuli)):
            w = windows_from(np.array(s.EEG.stimuli[t]).T[:, -LAST_S*FS:]); X.append(w)
            val += [sv[t]]*len(w); aro += [sa[t]]*len(w); subj += [si]*len(w); trial += [f"{si}_{t}"]*len(w)
    return np.concatenate(X).astype("float32"), np.array(val), np.array(aro), np.array(subj), np.array(trial)


def znorm(X):
    m = X.mean(2, keepdims=True); s = X.std(2, keepdims=True) + 1e-7
    return (X - m) / s


class EEGNet(nn.Module):
    def __init__(self, C, T, F1=8, D=2, F2=16, kern=64, drop=0.25):
        super().__init__()
        self.f = nn.Sequential(
            nn.Conv2d(1, F1, (1, kern), padding=(0, kern//2), bias=False), nn.BatchNorm2d(F1),
            nn.Conv2d(F1, F1*D, (C, 1), groups=F1, bias=False), nn.BatchNorm2d(F1*D), nn.ELU(),
            nn.AvgPool2d((1, 4)), nn.Dropout(drop),
            nn.Conv2d(F1*D, F1*D, (1, 16), padding=(0, 8), groups=F1*D, bias=False),
            nn.Conv2d(F1*D, F2, (1, 1), bias=False), nn.BatchNorm2d(F2), nn.ELU(),
            nn.AvgPool2d((1, 8)), nn.Dropout(drop))
        with torch.no_grad():
            n = self.f(torch.zeros(1, 1, C, T)).flatten(1).shape[1]
        self.fc = nn.Linear(n, 1)

    def forward(self, x):
        return self.fc(self.f(x).flatten(1)).squeeze(1)


def train_eval(Xtr, ytr, Xte, C, T, epochs=10, bs=256):
    net = EEGNet(C, T).to(DEV)
    opt = torch.optim.Adam(net.parameters(), 1e-3, weight_decay=1e-4)
    lossf = nn.BCEWithLogitsLoss()
    Xtr_t = torch.from_numpy(Xtr).unsqueeze(1); ytr_t = torch.from_numpy(ytr.astype("float32"))
    n = len(Xtr)
    for _ in range(epochs):
        net.train(); perm = torch.randperm(n)
        for i in range(0, n, bs):
            idx = perm[i:i+bs]
            opt.zero_grad()
            loss = lossf(net(Xtr_t[idx].to(DEV)), ytr_t[idx].to(DEV))
            loss.backward(); opt.step()
    net.eval(); probs = []
    with torch.no_grad():
        Xte_t = torch.from_numpy(Xte).unsqueeze(1)
        for i in range(0, len(Xte), 512):
            probs.append(torch.sigmoid(net(Xte_t[i:i+512].to(DEV))).cpu().numpy())
    return np.concatenate(probs)


def one_seed(X, y, subj, trial, seed):
    torch.manual_seed(seed); np.random.seed(seed)
    C, T = X.shape[1], X.shape[2]
    oof = np.zeros(len(y))
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=seed).split(X, y):
        oof[te] = train_eval(X[tr], y[tr], X[te], C, T)
    a1 = roc_auc_score(y, oof)
    oof = np.zeros(len(y))
    for tr, te in GroupKFold(5).split(X, y, groups=subj):
        oof[te] = train_eval(X[tr], y[tr], X[te], C, T)
    a2 = roc_auc_score(y, oof)
    op, oy = [], []
    for tr, te in LeaveOneGroupOut().split(X, y, groups=subj):
        p = train_eval(X[tr], y[tr], X[te], C, T); tt = trial[te]
        for ut in np.unique(tt):
            op.append(p[tt == ut].mean()); oy.append(y[te][tt == ut][0])
    a3 = roc_auc_score(oy, op)
    return float(a1), float(a2), float(a3)


if __name__ == "__main__":
    t0 = time.time()
    print(f"device={DEV} dataset={WHICH} seeds={NSEED}", flush=True)
    X, val, aro, subj, trial = (load_deap if WHICH == "DEAP" else load_dreamer)()
    X = znorm(X)
    print(f"[{WHICH}] {X.shape} loaded ({time.time()-t0:.0f}s)", flush=True)
    res = {}
    for tg, r in [("valence", val), ("arousal", aro)]:
        y = (r >= np.median(r)).astype(int)
        runs = []
        for seed in range(17, 17+NSEED):
            a1, a2, a3 = one_seed(X, y, subj, trial, seed)
            runs.append(dict(seed=seed, pooled=a1, subject_grouped=a2, loso=a3))
            print(f"  {WHICH} {tg} seed={seed}: pooled={a1:.3f} grouped={a2:.3f} loso={a3:.3f} "
                  f"({time.time()-t0:.0f}s)", flush=True)
        summ = {k: dict(mean=float(np.mean([r[k] for r in runs])),
                        sd=float(np.std([r[k] for r in runs])))
                for k in ("pooled", "subject_grouped", "loso")}
        res[tg] = dict(runs=runs, summary=summ)
        print(f"  == {WHICH} {tg} SUMMARY: " +
              "  ".join(f"{k}={summ[k]['mean']:.3f}+/-{summ[k]['sd']:.3f}" for k in summ), flush=True)
    (OUT / f"eegnet_{WHICH}.json").write_text(json.dumps(res, indent=2))
    print(f"DONE {time.time()-t0:.0f}s -> results/eegnet_{WHICH}.json", flush=True)
