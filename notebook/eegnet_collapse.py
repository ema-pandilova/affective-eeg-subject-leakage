"""Deep-model robustness check: the same window-pooled -> subject-grouped -> LOSO collapse,
but with an end-to-end EEGNet trained on RAW EEG (no handcrafted features). Confirms the
effect is not specific to the qEEG feature set or the gradient-boosted model.
Runs on GPU. DEAP (32 ch) and DREAMER (14 ch); valence and arousal; chance = 0.50 (median split).
"""
import pickle, time, warnings, numpy as np
from pathlib import Path
import scipy.io as sio
import os
import torch, torch.nn as nn, torch.nn.functional as F
from sklearn.model_selection import StratifiedKFold, GroupKFold, LeaveOneGroupOut
from sklearn.metrics import roc_auc_score
warnings.filterwarnings("ignore")
torch.manual_seed(17); np.random.seed(17)
DEV = "cuda:0" if torch.cuda.is_available() else "cpu"
FS, BASE_S, WIN_S, STEP_S, LAST_S = 128, 3, 4, 2, 60
# Set QEEG_DATA_ROOT to the folder containing data/deap/data_preprocessed_python/ and DREAMER.mat
ROOT = Path(os.environ.get("QEEG_DATA_ROOT", "."))

def windows_from(sig):  # sig: C x samples -> (n, C, WIN)
    T = WIN_S*FS; out=[]
    for st in range(0, sig.shape[1]-T+1, STEP_S*FS): out.append(sig[:, st:st+T])
    return np.stack(out) if out else np.empty((0, sig.shape[0], T))

def load_deap():
    X,val,aro,subj,trial=[],[],[],[],[]
    for sf in sorted((ROOT/"data/deap/data_preprocessed_python").glob("s*.dat")):
        s=int(sf.stem[1:]); dd=pickle.load(open(sf,"rb"),encoding="latin1")
        for t in range(dd["data"].shape[0]):
            w=windows_from(dd["data"][t,:32,BASE_S*FS:]); X.append(w)
            val+= [dd["labels"][t,0]]*len(w); aro+=[dd["labels"][t,1]]*len(w)
            subj+=[s]*len(w); trial+=[f"{s}_{t}"]*len(w)
    return np.concatenate(X).astype("float32"),np.array(val),np.array(aro),np.array(subj),np.array(trial)

def load_dreamer():
    X,val,aro,subj,trial=[],[],[],[],[]
    D=sio.loadmat(ROOT/"DREAMER.mat",struct_as_record=False,squeeze_me=True)["DREAMER"]
    for si,s in enumerate(D.Data):
        sv,sa=np.array(s.ScoreValence),np.array(s.ScoreArousal)
        for t in range(len(s.EEG.stimuli)):
            sig=np.array(s.EEG.stimuli[t]).T[:, -LAST_S*FS:]; w=windows_from(sig); X.append(w)
            val+=[sv[t]]*len(w); aro+=[sa[t]]*len(w); subj+=[si]*len(w); trial+=[f"{si}_{t}"]*len(w)
    return np.concatenate(X).astype("float32"),np.array(val),np.array(aro),np.array(subj),np.array(trial)

def znorm(X):  # per-window per-channel z-score (leak-free)
    m=X.mean(2,keepdims=True); s=X.std(2,keepdims=True)+1e-7; return (X-m)/s

class EEGNet(nn.Module):
    def __init__(self,C,T,F1=8,D=2,F2=16,kern=64,drop=0.25):
        super().__init__()
        self.f=nn.Sequential(
            nn.Conv2d(1,F1,(1,kern),padding=(0,kern//2),bias=False), nn.BatchNorm2d(F1),
            nn.Conv2d(F1,F1*D,(C,1),groups=F1,bias=False), nn.BatchNorm2d(F1*D), nn.ELU(),
            nn.AvgPool2d((1,4)), nn.Dropout(drop),
            nn.Conv2d(F1*D,F1*D,(1,16),padding=(0,8),groups=F1*D,bias=False),
            nn.Conv2d(F1*D,F2,(1,1),bias=False), nn.BatchNorm2d(F2), nn.ELU(),
            nn.AvgPool2d((1,8)), nn.Dropout(drop))
        with torch.no_grad(): n=self.f(torch.zeros(1,1,C,T)).flatten(1).shape[1]
        self.fc=nn.Linear(n,1)
    def forward(self,x): return self.fc(self.f(x).flatten(1)).squeeze(1)

def train_eval(Xtr,ytr,Xte,C,T,epochs=10,bs=256):
    net=EEGNet(C,T).to(DEV); opt=torch.optim.Adam(net.parameters(),1e-3,weight_decay=1e-4)
    lossf=nn.BCEWithLogitsLoss(); Xtr_t=torch.from_numpy(Xtr).unsqueeze(1); ytr_t=torch.from_numpy(ytr.astype("float32"))
    n=len(Xtr);
    for ep in range(epochs):
        net.train(); perm=torch.randperm(n)
        for i in range(0,n,bs):
            idx=perm[i:i+bs]; xb=Xtr_t[idx].to(DEV); yb=ytr_t[idx].to(DEV)
            opt.zero_grad(); loss=lossf(net(xb),yb); loss.backward(); opt.step()
    net.eval(); probs=[]
    with torch.no_grad():
        Xte_t=torch.from_numpy(Xte).unsqueeze(1)
        for i in range(0,len(Xte),512): probs.append(torch.sigmoid(net(Xte_t[i:i+512].to(DEV))).cpu().numpy())
    return np.concatenate(probs)

def run(name, X, y, subj, trial):
    C,T=X.shape[1],X.shape[2]
    # P1 pooled
    oof=np.zeros(len(y))
    for tr,te in StratifiedKFold(5,shuffle=True,random_state=17).split(X,y):
        oof[te]=train_eval(X[tr],y[tr],X[te],C,T)
    a1=roc_auc_score(y,oof)
    # P2 subject-grouped
    oof=np.zeros(len(y))
    for tr,te in GroupKFold(5).split(X,y,groups=subj):
        oof[te]=train_eval(X[tr],y[tr],X[te],C,T)
    a2=roc_auc_score(y,oof)
    # P3 LOSO trial-agg
    op,oy=[],[]
    for tr,te in LeaveOneGroupOut().split(X,y,groups=subj):
        p=train_eval(X[tr],y[tr],X[te],C,T); tt=trial[te]
        for ut in np.unique(tt): op.append(p[tt==ut].mean()); oy.append(y[te][tt==ut][0])
    a3=roc_auc_score(oy,op)
    print(f"EEGNet {name}: pooled={a1:.3f}  subject-grouped={a2:.3f}  LOSO={a3:.3f}",flush=True)

if __name__=="__main__":
    import sys
    which = sys.argv[1] if len(sys.argv)>1 else "ALL"          # DEAP | DREAMER | ALL
    targets = sys.argv[2].split(",") if len(sys.argv)>2 else ["valence","arousal"]
    if len(sys.argv)>3: DEV = sys.argv[3]
    t0=time.time(); print(f"device={DEV} which={which} targets={targets}",flush=True)
    loaders = {"DEAP":load_deap, "DREAMER":load_dreamer}
    for dsname in ([which] if which!="ALL" else ["DEAP","DREAMER"]):
        X,val,aro,subj,trial=loaders[dsname](); X=znorm(X)
        print(f"\n[{dsname}] {X.shape} loaded ({time.time()-t0:.0f}s)",flush=True)
        labs={"valence":val,"arousal":aro}
        for tg in targets:
            run(f"{dsname} {tg}",X,(labs[tg]>=np.median(labs[tg])).astype(int),subj,trial)
    print(f"\nTOTAL {time.time()-t0:.0f}s",flush=True)
