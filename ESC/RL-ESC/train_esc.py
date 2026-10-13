"""
Train an RL agent on ESCPlasmaEnv with Stable-Baselines3 SAC, then evaluate it
against the classical ESC (amp=0.1, freq=0.1 Hz, gain=4e-4) and plot the result.

    pip install gymnasium stable-baselines3 matplotlib
    python train_esc.py
"""
import matplotlib.pyplot as plt
import numpy as np
from stable_baselines3 import SAC
from stable_baselines3.common.env_util import make_vec_env

from esc_env import ESCPlasmaEnv

MODE = "direct"           # "direct" = RL replaces ESC, "tune" = RL tunes ESC params
TOTAL_TIMESTEPS = 50_000
ENV_KWARGS = dict(mode=MODE, episode_time=200.0, control_dt=1.0)

# ---------------------------------------------------------------- training
vec_env = make_vec_env(ESCPlasmaEnv, n_envs=4, env_kwargs=ENV_KWARGS, seed=0)
model = SAC("MlpPolicy", vec_env, verbose=1, seed=0)
model.learn(total_timesteps=TOTAL_TIMESTEPS)
model.save(f"sac_esc_{MODE}")


# -------------------------------------------------------------- evaluation
def rollout(env, policy, seed):
    obs, info = env.reset(seed=seed)
    t, r_hat, P = [info["t"]], [info["r_hat"]], [info["P"]]
    done = False
    while not done:
        obs, _, term, trunc, info = env.step(policy(obs))
        t.append(info["t"]); r_hat.append(info["r_hat"]); P.append(info["P"])
        done = term or trunc
    return np.array(t), np.array(r_hat), np.array(P), info["ideal_ratio"]


eval_seed = 123
rl_env = ESCPlasmaEnv(**ENV_KWARGS, initial_ratio=0.1)
t, r_rl, P_rl, ideal = rollout(rl_env, lambda o: model.predict(o, deterministic=True)[0], eval_seed)

esc_env = ESCPlasmaEnv(mode="tune", episode_time=200.0, initial_ratio=0.1)
esc_action = esc_env.params_to_action(0.1, 0.1, 4e-4)
_, r_esc, P_esc, _ = rollout(esc_env, lambda o: esc_action, eval_seed)

print(f"ideal ratio = {ideal:.4f}")
print(f"RL  final r_hat = {r_rl[-1]:.4f}  mean P (last 50 s) = {P_rl[-50:].mean():.3f}")
print(f"ESC final r_hat = {r_esc[-1]:.4f}  mean P (last 50 s) = {P_esc[-50:].mean():.3f}")

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot(t, r_rl, label=f"RL ({MODE})")
ax[0].plot(t, r_esc, label="classical ESC")
ax[0].axhline(ideal, ls="--", c="c", label="ideal ratio")
ax[0].set_xlabel("t [s]"); ax[0].set_ylabel(r"$\hat{r}$"); ax[0].legend(); ax[0].grid()
ax[1].plot(t, P_rl, label=f"RL ({MODE})")
ax[1].plot(t, P_esc, label="classical ESC")
ax[1].axhline(rl_env.P_ref, ls="--", c="c", label=r"ideal $n_D n_T$")
ax[1].set_xlabel("t [s]"); ax[1].set_ylabel(r"$n_D \times n_T$"); ax[1].legend(); ax[1].grid()
fig.tight_layout()
fig.savefig(f"eval_{MODE}.png", dpi=120)
plt.show()
