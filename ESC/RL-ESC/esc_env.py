"""
Gymnasium environment for RL-based extremum seeking of the D-T fuel ratio.

Plant (same physics as ESC.m):
    dn_D/dt = -a_D * n_D + (1 - r) * S
    dn_T/dt = -a_T * n_T + r * S
    S = PI controller keeping n_D + n_T at total_density_reference
    P = n_D * n_T   (objective to maximize)

r is the TRITIUM fraction of the fuel, consistent with the initial conditions
and ideal_ratio = a_T / (a_T + a_D) in main_fuelratio.m.

Two modes:
    "direct" : RL replaces ESC. Action = change in r_hat per decision step.
    "tune"   : classical ESC runs inside; RL sets (amplitude, frequency, gain).

The agent never sees ideal_ratio (model-free). It is only reported in `info`.
"""
import math

import gymnasium as gym
import numpy as np
from gymnasium import spaces


class ESCPlasmaEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        mode="direct",
        dt=0.01,                    # plant simulation step [s]
        control_dt=1.0,             # time between agent decisions [s]
        episode_time=200.0,         # episode length [s]
        history_len=4,              # past (r_hat, P) pairs in the observation
        max_delta_r=0.05,           # direct mode: max change of r_hat per decision
        action_penalty=0.0,         # direct mode: penalty on action^2
        initial_ratio=None,         # None -> random in [0.05, 0.95] each episode
        decay_time_spread=0.1,      # +- spread on 1.71 s and 1.66 s decay times
        amp_range=(0.01, 0.5),      # tune mode: dither amplitude range
        freq_range=(0.01, 0.5),     # tune mode: dither frequency range [Hz]
        gain_range=(1e-5, 1e-2),    # tune mode: optimizer gain range (log scale)
    ):
        super().__init__()
        assert mode in ("direct", "tune")
        self.mode = mode
        self.dt = dt
        self.steps_per_action = int(round(control_dt / dt))
        self.max_steps = int(round(episode_time / control_dt))
        self.history_len = history_len
        self.max_delta_r = max_delta_r
        self.action_penalty = action_penalty
        self.initial_ratio = initial_ratio
        self.decay_time_spread = decay_time_spread
        self.amp_range = amp_range
        self.freq_range = freq_range
        self.log_gain_range = (math.log10(gain_range[0]), math.log10(gain_range[1]))

        # Density controller (same as ESC.m)
        self.Kp = 3.129
        self.Ki = 2.482
        self.ref = 11.5            # e19 removed
        self.greenwald = 11.9      # e19 removed
        self.P_ref = 0.25 * self.ref ** 2   # max P at n_D = n_T = ref/2

        if mode == "direct":
            self.action_space = spaces.Box(-1.0, 1.0, shape=(1,), dtype=np.float32)
            obs_dim = 2 * history_len
        else:
            self.action_space = spaces.Box(-1.0, 1.0, shape=(3,), dtype=np.float32)
            obs_dim = 2 * history_len + 4   # + amp, freq, gain, gradient estimate xi
        self.obs_low = np.full(obs_dim, -3.0, dtype=np.float32)
        self.obs_high = np.full(obs_dim, 3.0, dtype=np.float32)
        self.observation_space = spaces.Box(self.obs_low, self.obs_high, dtype=np.float32)

    # ------------------------------------------------------------------ helpers
    def _map(self, a, lo, hi):
        return lo + (float(a) + 1.0) * 0.5 * (hi - lo)

    def action_to_params(self, action):
        """Tune mode: map action in [-1, 1]^3 to (amplitude, frequency, gain)."""
        amp = self._map(action[0], *self.amp_range)
        freq = self._map(action[1], *self.freq_range)
        gain = 10 ** self._map(action[2], *self.log_gain_range)
        return amp, freq, gain

    def params_to_action(self, amp, freq, gain):
        """Tune mode: inverse of action_to_params (useful for baselines)."""
        def inv(x, lo, hi):
            return 2.0 * (x - lo) / (hi - lo) - 1.0
        return np.array([
            inv(amp, *self.amp_range),
            inv(freq, *self.freq_range),
            inv(math.log10(gain), *self.log_gain_range),
        ], dtype=np.float32)

    def _set_dither_frequency(self, freq):
        self.freq = freq
        self.omega = 2 * math.pi * freq
        wc = self.omega / math.pi                 # same cutoff choice as ESC.m
        self.p_filt = math.exp(-wc * self.dt)     # ZOH pole of both filters

    def _get_obs(self):
        hist = np.array(self.history, dtype=np.float32).ravel()
        if self.mode == "direct":
            obs = hist
        else:
            extra = np.array([
                self.action_to_params_norm[0],
                self.action_to_params_norm[1],
                self.action_to_params_norm[2],
                np.tanh(self.xi / self.P_ref),
            ], dtype=np.float32)
            obs = np.concatenate([hist, extra])
        return np.clip(obs, self.obs_low, self.obs_high)

    # --------------------------------------------------------------- gym API
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        rng = self.np_random

        # Random plant each episode (same idea as rand() in ESC.m)
        s = self.decay_time_spread
        tau_D = 1.71 + (rng.random() - 0.5) * 2 * s
        tau_T = 1.66 + (rng.random() - 0.5) * 2 * s
        self.aD, self.aT = 1.0 / tau_D, 1.0 / tau_T
        self.ideal_ratio = self.aT / (self.aT + self.aD)

        # ZOH discretization of dx/dt = -a x + u  (what c2d does)
        self.AdD = math.exp(-self.aD * self.dt)
        self.AdT = math.exp(-self.aT * self.dt)
        self.BdD = (1 - self.AdD) / self.aD
        self.BdT = (1 - self.AdT) / self.aT

        r0 = self.initial_ratio if self.initial_ratio is not None else rng.uniform(0.05, 0.95)
        self.r_hat = float(r0)
        self.nD = 0.25 * (1 - r0) * self.ref
        self.nT = 0.25 * r0 * self.ref
        self.int_e = 0.0
        self.t = 0.0
        self.step_count = 0

        # ESC internals (tune mode)
        self.phase = 0.0
        self.amp, self.gain = 0.1, 4e-4
        self._set_dither_frequency(0.1)
        P0 = self.nD * self.nT
        self.hp_x_prev = P0       # start HP filter at P0 to avoid an initial spike
        self.hp_y_prev = 0.0
        self.lp_x_prev = 0.0
        self.lp_y_prev = 0.0
        self.xi = 0.0
        self.action_to_params_norm = self.params_to_action(self.amp, self.freq, self.gain)

        self.history = [(self.r_hat, P0 / self.P_ref)] * self.history_len
        return self._get_obs(), self._info(P0)

    def step(self, action):
        action = np.clip(np.asarray(action, dtype=np.float32), -1.0, 1.0)

        if self.mode == "direct":
            self.r_hat = min(max(self.r_hat + float(action[0]) * self.max_delta_r, 0.0), 1.0)
        else:
            self.amp, freq, self.gain = self.action_to_params(action)
            self._set_dither_frequency(freq)
            self.action_to_params_norm = action

        P_mean, total_max = self._simulate_interval()

        reward = P_mean / self.P_ref
        if self.mode == "direct":
            reward -= self.action_penalty * float(action[0]) ** 2

        self.history = self.history[1:] + [(self.r_hat, P_mean / self.P_ref)]
        self.step_count += 1
        truncated = self.step_count >= self.max_steps
        info = self._info(P_mean)
        info["greenwald_exceeded"] = total_max > self.greenwald
        return self._get_obs(), float(reward), False, truncated, info

    def _simulate_interval(self):
        dt, tune = self.dt, self.mode == "tune"
        p = self.p_filt
        P_sum, total_max = 0.0, 0.0
        for _ in range(self.steps_per_action):
            # Current r (dither only in tune mode)
            if tune:
                s = math.sin(self.phase)
                r = self.r_hat + self.amp * s
            else:
                r = self.r_hat
            r = min(max(r, 0.0), 1.0)

            # Density PI controller
            e = self.ref - (self.nD + self.nT)
            self.int_e += e * dt
            S = max(self.Kp * e + self.Ki * self.int_e, 0.0)

            # Fuel split and density update (r = tritium fraction)
            self.nD = self.AdD * self.nD + self.BdD * (1 - r) * S
            self.nT = self.AdT * self.nT + self.BdT * r * S
            P = self.nD * self.nT
            P_sum += P
            total_max = max(total_max, self.nD + self.nT)

            if tune:
                # High-pass  (z-1)/(z-p)
                hp = P - self.hp_x_prev + p * self.hp_y_prev
                self.hp_x_prev, self.hp_y_prev = P, hp
                # Demodulation (2/a) sin(wt)
                demod = hp * (2.0 / self.amp) * s
                # Low-pass  (1-p)/(z-p)
                lp = (1 - p) * self.lp_x_prev + p * self.lp_y_prev
                self.lp_x_prev, self.lp_y_prev = demod, lp
                self.xi = lp
                # Integrator k/s
                self.r_hat = min(max(self.r_hat + self.gain * self.xi * dt, 0.0), 1.0)
                self.phase = (self.phase + self.omega * dt) % (2 * math.pi)

            self.t += dt
        return P_sum / self.steps_per_action, total_max

    def _info(self, P):
        return {
            "t": self.t,
            "r_hat": self.r_hat,
            "P": P,
            "ideal_ratio": self.ideal_ratio,
            "r_error": self.r_hat - self.ideal_ratio,
            "nD": self.nD,
            "nT": self.nT,
        }


if __name__ == "__main__":
    from gymnasium.utils.env_checker import check_env

    for m in ("direct", "tune"):
        check_env(ESCPlasmaEnv(mode=m), skip_render_check=True)
        print(f"check_env passed: {m}")
