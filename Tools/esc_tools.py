"""
Shared helpers for the analysis notebooks.

Everything that used to be copied from notebook to notebook lives here:
  * one plot style for all figures            -> apply_style()
  * the model constants                        -> N_REF, ALPHA_D, ...
  * the averaged-ESC formulas                  -> c_factor(), lam_avg(), dither_loss()
  * the standard plots used in every notebook  -> outcome_bar(), scatter_grid(), ...

Use it from a notebook with

    import esc_tools as esc
    esc.apply_style()

To change how every plot in the repository looks, edit apply_style() and COLORS.
"""
from __future__ import annotations

import inspect

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from cycler import cycler

# --------------------------------------------------------------------------
# Model constants (same values as in the MATLAB scripts)
# --------------------------------------------------------------------------
N_REF = 11.5                              # total density reference [1e19 m^-3]
ALPHA_D, ALPHA_T = 1 / 1.71, 1 / 1.66     # nominal loss rates [1/s]
ALPHA_BAR = 0.5 * (ALPHA_D + ALPHA_T)     # mean loss rate = corner frequency of the plasma response [1/s]
T_END = 100.0                             # run length [s]
E_MAX = 0.25 * N_REF**2 * T_END           # n_D = n_T = n_ref/2 for the whole run (not reachable: runs start at 25 % density)

ESC_PARAMS = ['optimizer_gain', 'dither_amplitude', 'dither_frequency']
PLANT_PARAMS = ['r_ideal_0', 'lambda_r_ideal']

# Window in which the ESC is "well tuned" (see the report, Sec. 3.2-3.3)
LAM_WINDOW = (0.1, 3.0)                   # averaged convergence rate [1/s]
L_DITH_MAX = 1.0                          # predicted dither loss [energy units]

# --------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------
COLORS = {
    'esc': '#1f5fa8',      # anything measured with ESC (main colour)
    'fixed': '#e69f00',    # fixed fuel ratio r = 0.5
    'ideal': '#222222',    # theoretical / ideal reference lines
    'grey': '#8a8a8a',     # secondary curves, second y-axis
    'bad': '#d55e00',      # failures: not converged, ESC loses
    'light': '#cfdcef',    # light fill of the main colour
}
CYCLE = [COLORS['esc'], COLORS['fixed'], '#009e73', '#cc79a7', '#56b4e9', COLORS['bad'], '#7a5195', COLORS['grey']]

LABELS = {
    'optimizer_gain': 'optimizer gain $k$',
    'log10_gain': r'$\log_{10}$ optimizer gain $k$',
    'dither_amplitude': 'dither amplitude $a$',
    'dither_frequency': 'dither frequency $f$ [Hz]',
    'convergence_time': 'convergence time [s]',
    'converged': 'converged',
    'r_ideal_0': r'initial ideal ratio $r_{\mathrm{ideal},0}$',
    'lambda_r_ideal': r'drift rate $\lambda$ [s$^{-1}$]',
    'ideal_ratio': r'ideal ratio $r_\mathrm{ideal}$',
    'n_D_decay_rate': r'D loss rate $\alpha_D$ [s$^{-1}$]',
    'n_T_decay_rate': r'T loss rate $\alpha_T$ [s$^{-1}$]',
    'energy_ESC': 'energy with ESC',
    'energy_const': 'energy with fixed $r = 0.5$',
    'energy_max': 'energy at ideal densities',
    'energy_gain': r'energy gain $E_\mathrm{ESC} - E_{r=0.5}$',
    'choose_ESC': 'ESC beats $r = 0.5$',
    'lam_avg': r'averaged ESC rate $\lambda_\mathrm{avg}$ [s$^{-1}$]',
    'L_dith': r'predicted dither loss $L_\mathrm{dith}$',
}
SHORT = {  # short names for heat-map ticks and 3-D axes
    'optimizer_gain': 'gain k', 'log10_gain': 'log10 k', 'dither_amplitude': 'amplitude a', 'dither_frequency': 'frequency f',
    'convergence_time': 'conv. time', 'r_ideal_0': 'r_ideal,0', 'lambda_r_ideal': 'drift λ', 'ideal_ratio': 'r_ideal',
    'n_D_decay_rate': 'α_D', 'n_T_decay_rate': 'α_T', 'energy_ESC': 'E_ESC', 'energy_const': 'E_fixed',
    'energy_gain': 'E gain', 'choose_ESC': 'ESC wins', 'converged': 'converged', 'lam_avg': 'λ_avg', 'L_dith': 'L_dith',
}


def label(col):
    """Readable axis label for a column name."""
    return LABELS.get(col, col)


def apply_style():
    """Set the common look of all figures (matplotlib, seaborn, pandas, plotly)."""
    sns.set_theme(context='notebook', style='ticks')
    mpl.rcParams.update({
        'figure.figsize': (6.4, 4.0), 'figure.dpi': 100, 'savefig.dpi': 300, 'savefig.bbox': 'tight',
        'font.size': 10, 'axes.titlesize': 11, 'axes.titleweight': 'regular', 'axes.titlelocation': 'left',
        'axes.labelsize': 10, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
        'legend.fontsize': 9, 'legend.frameon': False,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.color': '#e6e6e6', 'grid.linewidth': 0.6,
        'axes.prop_cycle': cycler(color=CYCLE),
        'lines.linewidth': 1.6, 'lines.markersize': 4, 'image.cmap': 'viridis',
    })
    pd.set_option('display.max_columns', 200)
    try:
        import plotly.io as pio
        pio.templates.default = 'plotly_white'
    except ImportError:
        pass


def panel_letter(ax, letter):
    """Bold panel letter above the top-left corner of an axes."""
    ax.text(-0.14, 1.06, letter, transform=ax.transAxes, fontsize=12, fontweight='bold', va='bottom', ha='right')


def _twin(ax):
    """Second y-axis with a visible right spine and no extra grid."""
    ax2 = ax.twinx()
    ax2.spines['right'].set_visible(True)
    ax2.grid(False)
    return ax2


def _sample(df, n, seed=0):
    """Random subset of at most n rows (plots stay readable and notebooks stay small)."""
    return df if n is None or len(df) <= n else df.sample(n, random_state=seed)


# --------------------------------------------------------------------------
# Averaged-ESC formulas
# --------------------------------------------------------------------------
def c_factor(f, alpha_bar=ALPHA_BAR):
    """How much of the gradient the ESC loop "sees" at dither frequency f [Hz].

    c(w) = |G H| cos(phi), with
      G(s) = alpha_bar / (s + alpha_bar)   response of the D/T split to the fuel ratio,
      H(s) = s / (s + w/pi)                the high-pass filter (cut-off tied to the dither).
    c -> 0.93 for slow dithers and falls off steeply above the plasma corner frequency.
    """
    w = 2 * np.pi * np.asarray(f, dtype=float)
    phi = -np.arctan(w / alpha_bar) + np.arctan(1 / np.pi)
    mag = alpha_bar / np.sqrt(alpha_bar**2 + w**2) / np.sqrt(1 + 1 / np.pi**2)
    return mag * np.cos(phi)


def lam_avg(k, f, alpha_bar=ALPHA_BAR):
    """Averaged ESC convergence rate [1/s]:  d(r_hat)/dt = -lam_avg (r_hat - r_ideal).

    lam_avg = 2 n_ref^2 k c(w).  Predicted time to enter a 5 % band from r_hat = 0: ln(20)/lam_avg.
    """
    return 2 * N_REF**2 * np.asarray(k, dtype=float) * c_factor(f, alpha_bar)


def dither_loss(a, f, alpha_bar=ALPHA_BAR, T=T_END):
    """Predicted energy lost to the dither oscillation over a run of length T."""
    w = 2 * np.pi * np.asarray(f, dtype=float)
    a = np.asarray(a, dtype=float)
    return T * N_REF**2 / 4 * 2 * a**2 * alpha_bar**2 / (alpha_bar**2 + w**2)


def add_esc_quantities(df, alpha_bar=ALPHA_BAR):
    """Copy of df with lam_avg, L_dith and (if both energies exist) energy_gain."""
    d = df.copy()
    d['lam_avg'] = lam_avg(d['optimizer_gain'], d['dither_frequency'], alpha_bar)
    d['L_dith'] = dither_loss(d['dither_amplitude'], d['dither_frequency'], alpha_bar)
    if {'energy_ESC', 'energy_const'} <= set(d.columns):
        d['energy_gain'] = d['energy_ESC'] - d['energy_const']
    return d


def well_tuned(d):
    """Boolean mask: lam_avg inside LAM_WINDOW and predicted dither loss below L_DITH_MAX."""
    return (d['lam_avg'] > LAM_WINDOW[0]) & (d['lam_avg'] < LAM_WINDOW[1]) & (d['L_dith'] < L_DITH_MAX)


def _log_bins(values, edges):
    """Group by log10(values) in the given bin edges; return (bin centres, groupby)."""
    return pd.cut(np.log10(values), edges)


def _centres(group):
    return 10 ** np.array([(iv.left + iv.right) / 2 for iv in group.size().index])


# --------------------------------------------------------------------------
# Standard plots
# --------------------------------------------------------------------------
def outcome_bar(series, names=('no', 'yes'), title='', xlabel='', ax=None):
    """Bar chart of a 0/1 column with the share of each outcome written on the bars."""
    ax = ax or plt.subplots(figsize=(4.2, 3.4))[1]
    counts = series.astype(int).value_counts().reindex([0, 1], fill_value=0)
    bars = ax.bar(list(names), counts.values, color=[COLORS['bad'], COLORS['esc']], width=0.6)
    for bar, c in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f'{c / counts.sum():.1%}', ha='center', va='bottom')
    ax.set_xlabel(xlabel); ax.set_ylabel('number of runs'); ax.set_title(title)
    ax.grid(axis='x', visible=False); ax.margins(y=0.12)
    return ax


def time_hist(series, bins=60, title='', xlabel=None, ax=None):
    """Histogram of a time column (NaN = not converged is ignored)."""
    ax = ax or plt.subplots(figsize=(5.2, 3.4))[1]
    data = series.dropna()
    ax.hist(data, bins=bins, color=COLORS['esc'], edgecolor='white', linewidth=0.3)
    ax.axvline(data.median(), color=COLORS['ideal'], ls='--', lw=1, label=f'median {data.median():.1f} s')
    ax.set_xlabel(xlabel or label(series.name)); ax.set_ylabel('number of runs'); ax.set_title(title)
    ax.legend()
    return ax


def scatter_grid(df, x_cols, y_cols, *, sample=20000, logx=('optimizer_gain',), ylim=None, ylabel=None,
                 hline=None, hline_label=None, title=None, yscale=None, seed=0):
    """One row of scatter plots: the same y column(s) against each column in x_cols.

    y_cols may be one name or a list (then each gets its own colour and a legend).
    """
    y_cols = [y_cols] if isinstance(y_cols, str) else list(y_cols)
    d = _sample(df.dropna(subset=y_cols), sample, seed)
    fig, axes = plt.subplots(1, len(x_cols), figsize=(3.3 * len(x_cols) + 0.6, 3.4), sharey=True, squeeze=False)
    for ax, x in zip(axes[0], x_cols):
        for y, color in zip(y_cols, CYCLE):
            ax.scatter(d[x], d[y], s=4, alpha=0.35, linewidths=0, color=color, rasterized=True,
                       label=label(y) if len(y_cols) > 1 else None)
        if hline is not None:
            ax.axhline(hline, color=COLORS['ideal'], ls='--', lw=1, label=hline_label)
        if x in logx:
            ax.set_xscale('log')
        if yscale:
            ax.set_yscale(yscale[0], **yscale[1]) if isinstance(yscale, tuple) else ax.set_yscale(yscale)
        ax.set_xlabel(label(x))
        if ylim:
            ax.set_ylim(*ylim)
    axes[0, 0].set_ylabel(ylabel or (label(y_cols[0]) if len(y_cols) == 1 else 'energy'))
    if title:
        fig.suptitle(title, x=0.01, ha='left', fontsize=11)
    fig.tight_layout()
    if len(y_cols) > 1 or hline_label:      # one legend below the panels, so it never covers data
        handles, names = axes[0, -1].get_legend_handles_labels()
        leg = fig.legend(handles, names, loc='upper center', bbox_to_anchor=(0.5, 0.02), ncol=len(names), markerscale=2.5)
        for h in leg.legend_handles:
            h.set_alpha(1)
    return fig


def pair_plot(df, cols, *, sample=5000, title=None, seed=0):
    """Pair plot of the given columns on a random subset; the gain is shown as log10."""
    d = _sample(df.dropna(subset=cols), sample, seed).copy()
    cols = list(cols)
    if 'optimizer_gain' in cols:
        d['log10_gain'] = np.log10(d['optimizer_gain'])
        cols[cols.index('optimizer_gain')] = 'log10_gain'
    d = d[cols].rename(columns={c: label(c) for c in cols})
    grid = sns.pairplot(d, height=1.9, corner=False, diag_kws=dict(color=COLORS['esc'], edgecolor='white', linewidth=0.2),
                        plot_kws=dict(s=5, alpha=0.35, linewidth=0, color=COLORS['esc'], rasterized=True))
    if title:
        grid.figure.suptitle(title, x=0.01, ha='left', fontsize=11, y=1.01)
    return grid


def corr_heatmap(df, cols, title='Pearson correlation', ax=None):
    """Annotated correlation matrix, colour scale fixed to [-1, 1] and centred at 0."""
    size = 0.62 * len(cols) + 1.6
    ax = ax or plt.subplots(figsize=(size + 0.8, size))[1]
    corr = df[cols].corr().rename(index=SHORT, columns=SHORT)
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', vmin=-1, vmax=1, center=0, square=True,
                annot_kws={'size': 8}, cbar_kws={'label': 'correlation', 'shrink': 0.8}, ax=ax)
    ax.set_title(title); ax.grid(False)
    return ax


def convergence_vs_rate(df, alpha_bar=ALPHA_BAR, others=None):
    """Three panels: convergence fraction and time against lam_avg, and the effect of the amplitude.

    others: optional {name: dataframe} drawn in grey in panels a and b for comparison.
    Returns (figure, dataframe of the runs inside LAM_WINDOW).
    """
    def stats(data, a_bar):
        d = data.copy()
        d['lam_avg'] = lam_avg(d['optimizer_gain'], d['dither_frequency'], a_bar)
        g = d.groupby(_log_bins(d['lam_avg'], np.arange(-3.5, 2.01, 0.25)), observed=True)
        t = g['convergence_time']
        return d, _centres(g), g['converged'].mean().values, t.median().values, t.quantile(0.25).values, t.quantile(0.75).values

    d, x, pconv, med, q1, q3 = stats(df, alpha_bar)
    fig, axs = plt.subplots(1, 3, figsize=(13, 3.8))

    ax = axs[0]
    for name, other in (others or {}).items():
        _, xo, po, *_ = stats(other, ALPHA_BAR)
        ax.plot(xo, po, 's--', color=COLORS['grey'], ms=3, lw=1, label=name)
    ax.plot(x, pconv, 'o-', color=COLORS['esc'], label='this dataset' if others else None)
    ax.axvspan(*LAM_WINDOW, color=COLORS['esc'], alpha=0.08, lw=0)
    ax.text(0.55, 0.08, f'{LAM_WINDOW[0]:g}–{LAM_WINDOW[1]:g} s$^{{-1}}$', ha='center', color=COLORS['esc'], fontsize=9)
    ax.set_xscale('log'); ax.set_xlabel(r'$\lambda_\mathrm{avg}=2n_\mathrm{ref}^2\,k\,c(\omega)$ [s$^{-1}$]')
    ax.set_ylabel('fraction of runs converged'); ax.set_title('Convergence is set by one combined rate')
    if others:
        ax.legend(loc='upper left')

    ax = axs[1]
    m = ~np.isnan(med)
    for name, other in (others or {}).items():
        _, xo, _, mo, *_ = stats(other, ALPHA_BAR)
        ax.plot(xo[~np.isnan(mo)], mo[~np.isnan(mo)], 's--', color=COLORS['grey'], ms=3, lw=1, label=f'{name} (median)')
    ax.fill_between(x[m], q1[m], q3[m], color=COLORS['esc'], alpha=0.2, lw=0)
    ax.plot(x[m], med[m], 'o-', color=COLORS['esc'], label='median (band: IQR)')
    tt = np.logspace(-2, 1.5, 50)
    ax.plot(tt, np.log(20) / tt, ':', color=COLORS['ideal'], lw=1.2, label=r'$\ln 20/\lambda_\mathrm{avg}$ (averaging theory)')
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_ylim(1, 100)
    ax.set_xlabel(r'$\lambda_\mathrm{avg}$ [s$^{-1}$]'); ax.set_ylabel('convergence time [s]')
    ax.legend(loc='upper right'); ax.set_title('Too slow, then optimal, then unstable')

    win = d[(d['lam_avg'] > LAM_WINDOW[0]) & (d['lam_avg'] < LAM_WINDOW[1])]
    gw = win.groupby(pd.cut(win['dither_amplitude'], np.arange(0, 1.01, 0.1)), observed=True)
    amid = np.array([(iv.left + iv.right) / 2 for iv in gw.size().index])
    ax = axs[2]
    ax.plot(amid, gw['converged'].mean().values, 'o-', color=COLORS['esc'])
    ax.set_ylim(0, 1.05); ax.set_xlabel(label('dither_amplitude')); ax.set_ylabel('fraction converged', color=COLORS['esc'])
    ax2 = _twin(ax)
    ax2.plot(amid, gw['convergence_time'].median().values, 's--', color=COLORS['grey'])
    ax2.set_ylim(0, 20); ax2.set_ylabel('median convergence time [s]', color=COLORS['grey'])
    ax.set_title('Effect of the dither amplitude inside the window')

    for a_, l_ in zip(axs, 'abc'):
        panel_letter(a_, l_)
    fig.tight_layout()
    return fig, win


def energy_vs_tuning(df):
    """Two panels: energy gain of ESC over r = 0.5 against the dither loss and against lam_avg.

    Returns (figure, dataframe with lam_avg, L_dith and energy_gain added).
    """
    d = add_esc_quantities(df)
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.8))
    panels = [('L_dith', np.arange(-4, 4.01, 0.5), LABELS['L_dith'] + ' (energy units)', 'ESC loses once the dither costs more than about 3'),
              ('lam_avg', np.arange(-7, 2.51, 0.5), LABELS['lam_avg'], 'ESC loses when the loop is too fast')]
    for ax, (col, edges, xlabel, title) in zip(axs, panels):
        g = d.groupby(_log_bins(d[col], edges), observed=True)
        mid = _centres(g)
        ax.axhline(0, color=COLORS['grey'], lw=0.8)
        ax.fill_between(mid, g['energy_gain'].quantile(0.25), g['energy_gain'].quantile(0.75), color=COLORS['esc'], alpha=0.2, lw=0)
        ax.plot(mid, g['energy_gain'].median(), 'o-', color=COLORS['esc'])
        ax.set_xscale('log'); ax.set_yscale('symlog', linthresh=10)
        ax.set_xlabel(xlabel); ax.set_ylabel(LABELS['energy_gain'] + ' (median, band: IQR)', color=COLORS['esc'])
        ax2 = _twin(ax)
        ax2.plot(mid, g['choose_ESC'].mean(), 's--', color=COLORS['grey'], ms=3.5)
        ax2.set_ylim(0, 1.02); ax2.set_ylabel('fraction of runs where ESC wins', color=COLORS['grey'])
        ax.set_title(title)
    for a_, l_ in zip(axs, 'ab'):
        panel_letter(a_, l_)
    fig.tight_layout()
    return fig, d


def plant_map(df, color, *, sample=20000, title='', cmap='coolwarm', vmin=None, vmax=None, clabel=None, seed=0):
    """Scatter of the plant parameters (r_ideal_0 against drift rate) coloured by a column."""
    d = _sample(df, sample, seed)
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    sc = ax.scatter(d['r_ideal_0'], d['lambda_r_ideal'] * 1e3, c=d[color], cmap=cmap, vmin=vmin, vmax=vmax,
                    s=4, linewidths=0, rasterized=True)
    fig.colorbar(sc, ax=ax, pad=0.02).set_label(clabel or label(color))
    ax.set_xlabel(label('r_ideal_0')); ax.set_ylabel(r'drift rate $\lambda$ [10$^{-3}$ s$^{-1}$]'); ax.set_title(title)
    fig.tight_layout()
    return fig


def gain_boxplot(dfs):
    """Box per plant of the energy gain of well-tuned ESC runs, with the largest gain reached in any run.

    dfs: {plant name: dataframe}.  Returns (figure, summary table).
    """
    e_ceil = max(d['energy_ESC'].max() for d in dfs.values())   # best ESC energy in any run (E_MAX is not reachable)
    data, bound, rows = [], [], []
    for name, raw in dfs.items():
        d = add_esc_quantities(raw)
        tuned = d[well_tuned(d)]
        data.append(tuned['energy_gain'].values)
        bound.append(e_ceil - d['energy_const'].iloc[0])        # energy_const is the same in every row of one plant
        rows.append({'plant': name, 'well-tuned runs': len(tuned), 'ESC wins': tuned['choose_ESC'].mean(),
                     'median gain': tuned['energy_gain'].median(), 'upper bound': bound[-1]})
    fig, ax = plt.subplots(figsize=(7.2, 0.5 * len(data) + 1.6))
    y = np.arange(len(data))
    horizontal = (dict(orientation='horizontal') if 'orientation' in inspect.signature(ax.boxplot).parameters
                  else dict(vert=False))                        # matplotlib >= 3.10 / older
    line = dict(color=COLORS['esc'])
    ax.boxplot(data, positions=y, widths=0.55, showfliers=False, patch_artist=True, medianprops=line, whiskerprops=line,
               capprops=line, boxprops=dict(facecolor=COLORS['light'], edgecolor=COLORS['esc']), **horizontal)
    ax.scatter(bound, y, marker='D', color=COLORS['ideal'], s=16, zorder=3, label=r'upper bound $E_\mathrm{ceil}-E_{r=0.5}$')
    ax.axvline(0, color=COLORS['grey'], lw=0.8)
    ax.set_yticks(y); ax.set_yticklabels(list(dfs)); ax.invert_yaxis(); ax.set_xscale('symlog', linthresh=10)
    ax.set_xlabel(LABELS['energy_gain'] + ' (well-tuned ESC)'); ax.set_ylabel('plant')
    ax.legend(loc='lower right', bbox_to_anchor=(1.0, 1.0)); ax.set_title('Energy gain of the well-tuned ESC runs, per plant')
    fig.tight_layout()
    return fig, pd.DataFrame(rows).set_index('plant')


def gain_vs_plant(df, *, sample=20000, title='', seed=0):
    """Energy gain of ESC over r = 0.5 against the initial ideal ratio, coloured by the drift rate."""
    d = _sample(add_esc_quantities(df), sample, seed)
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    sc = ax.scatter(d['r_ideal_0'], d['energy_gain'], c=d['lambda_r_ideal'] * 1e3, cmap='coolwarm', vmin=-2, vmax=2,
                    s=4, linewidths=0, rasterized=True)
    ax.axhline(0, color=COLORS['grey'], lw=0.8)
    fig.colorbar(sc, ax=ax, pad=0.02).set_label(r'drift rate $\lambda$ [10$^{-3}$ s$^{-1}$]')
    ax.set_xlabel(label('r_ideal_0')); ax.set_ylabel(label('energy_gain')); ax.set_title(title)
    fig.tight_layout()
    return fig


def plant_grid(dfs, x, y='energy_ESC', *, sample=5000, ylim=None, logx=None, seed=0):
    """Small multiples, one panel per plant: y against x, with that plant's fixed-ratio energy as a line.

    dfs: {plant name: dataframe}.
    """
    logx = (x == 'optimizer_gain') if logx is None else logx
    ncols = min(4, len(dfs)); nrows = int(np.ceil(len(dfs) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.3 * ncols + 0.6, 2.9 * nrows + 0.4), sharex=True, sharey=True, squeeze=False)
    for ax, (name, raw) in zip(axes.flat, dfs.items()):
        d = _sample(raw.dropna(subset=[x, y]), sample, seed)
        ax.scatter(d[x], d[y], s=4, alpha=0.35, linewidths=0, color=COLORS['esc'], rasterized=True, label=label(y))
        if y == 'energy_ESC':
            ax.axhline(raw['energy_const'].iloc[0], color=COLORS['fixed'], lw=1.5, label=label('energy_const'))
        if logx:
            ax.set_xscale('log')
        if ylim:
            ax.set_ylim(*ylim)
        ax.set_title(name)
    for ax in axes.flat[len(dfs):]:
        ax.axis('off')
    for ax in axes[-1]:
        ax.set_xlabel(label(x))
    for ax in axes.flat[max(0, len(dfs) - ncols):len(dfs)]:    # panels above an empty slot still need their x label
        ax.set_xlabel(label(x)); ax.tick_params(labelbottom=True)
    for row in axes:
        row[0].set_ylabel(label(y))
    fig.tight_layout()
    handles, names = axes[0, 0].get_legend_handles_labels()
    if len(dfs) < axes.size:                 # an empty slot in the grid: put the legend there
        leg = axes.flat[len(dfs)].legend(handles, names, loc='center', markerscale=2.5)
    else:                                    # otherwise below the panels
        leg = fig.legend(handles, names, loc='upper center', bbox_to_anchor=(0.5, 0.02), ncol=len(names), markerscale=2.5)
    for h in leg.legend_handles:
        h.set_alpha(1)
    return fig


def gain_ecdf(dfs, title='Energy gain of ESC over fixed r = 0.5, all runs'):
    """Cumulative distribution of the energy gain for each plant (fraction of runs with a gain below x)."""
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for (name, raw), color in zip(dfs.items(), CYCLE):
        gain = np.sort((raw['energy_ESC'] - raw['energy_const']).values)
        step = max(1, len(gain) // 2000)                      # 2000 points per curve are plenty
        ax.plot(gain[::step], (np.arange(len(gain)) / len(gain))[::step], color=color, label=name)
    ax.axvline(0, color=COLORS['ideal'], ls='--', lw=1)
    ax.set_xscale('symlog', linthresh=1); ax.set_ylim(0, 1)
    ax.set_xlabel(label('energy_gain') + '  (left of the dashed line: ESC loses)'); ax.set_ylabel('fraction of runs below')
    ax.legend(title='plant', loc='upper left', bbox_to_anchor=(1.01, 1.0)); ax.set_title(title)
    fig.tight_layout()
    return fig


def loss_curves(histories, ncols=None):
    """Training and cross-validation loss per epoch; histories = {model name: history dict}.

    ncols: number of panels per row (default: all panels in one row).
    """
    n = len(histories)
    ncols = n if ncols is None else min(ncols, n)
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.2 * ncols + 0.4, 3.2 * nrows), sharey=True, squeeze=False)
    for ax in axes.ravel()[n:]:
        ax.set_visible(False)
    for ax, (name, h) in zip(axes.ravel(), histories.items()):
        ax.plot(h['loss'], color=COLORS['esc'], label='training')
        ax.plot(h['val_loss'], color=COLORS['fixed'], label='cross-validation')
        ax.set_xlabel('epoch'); ax.set_title(name)
    for row in axes:
        row[0].set_ylabel('binary cross-entropy loss')
    axes[0, ncols - 1].legend()
    fig.tight_layout()
    return fig


def scatter3d(df, color, *, sample=20000, title='', discrete=False, range_color=None, seed=0):
    """Interactive 3-D scatter of the three ESC parameters (gain on a log axis), coloured by a column.

    Only a random subset is drawn so the notebook stays small; raise `sample` for a denser view.
    """
    import plotly.express as px
    d = _sample(df.dropna(subset=[color]), sample, seed)
    names = {c: SHORT.get(c, c) for c in ESC_PARAMS + [color]}
    if discrete:
        d = d.assign(**{color: d[color].astype(int).map({0: 'no', 1: 'yes'})})
        fig = px.scatter_3d(d, x='optimizer_gain', y='dither_amplitude', z='dither_frequency', color=color, log_x=True,
                            color_discrete_map={'no': COLORS['bad'], 'yes': COLORS['esc']},
                            category_orders={color: ['no', 'yes']}, labels=names, title=title)
    else:
        fig = px.scatter_3d(d, x='optimizer_gain', y='dither_amplitude', z='dither_frequency', color=color, log_x=True,
                            color_continuous_scale='Viridis', range_color=range_color, labels=names, title=title)
    fig.update_traces(marker=dict(size=3))
    fig.update_layout(width=760, height=560, margin=dict(l=0, r=0, t=40, b=0))
    return fig


# ---- smoothed maps of the parameter space -----------------------------------

def bins_for(n_runs, runs_per_bin=20, low=20, high=100):
    """Number of bins per axis so that a square grid holds about `runs_per_bin` runs per bin."""
    return int(np.clip(np.sqrt(n_runs / runs_per_bin), low, high))


def binned_map(x, y, values, x_edges, y_edges, *, statistic='mean', smooth=1.5, min_weight=0.5):
    """Map of `values` over the grid (x_edges, y_edges), smoothed with a Gaussian of `smooth` bins.

    statistic='mean'  : smoothed mean = (smoothed sum of the values) / (smoothed number of runs), i.e. every run
                        counts equally and empty bins do not pull the result towards zero. Bins with a smoothed
                        number of runs below `min_weight` are NaN.
    statistic='median': median per bin, then averaged over neighbouring non-empty bins with the same Gaussian.
    smooth=0 gives the plain binned statistic. Returns an array of shape (len(x_edges) - 1, len(y_edges) - 1),
    to be drawn with ax.pcolormesh(x_edges, y_edges, result.T).
    """
    from scipy.ndimage import gaussian_filter
    from scipy.stats import binned_statistic_2d
    x, y, values = (np.asarray(a, dtype=float) for a in (x, y, values))
    with np.errstate(invalid='ignore', divide='ignore'):
        if statistic == 'mean':
            total, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges], weights=values)
            count, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
            if smooth:
                total = gaussian_filter(total, smooth, mode='constant')
                count = gaussian_filter(count, smooth, mode='constant')
            return np.where(count >= min_weight, total / count, np.nan)
        per_bin, _, _, _ = binned_statistic_2d(x, y, values, statistic=statistic, bins=[x_edges, y_edges])
        if not smooth:
            return per_bin
        filled = ~np.isnan(per_bin)
        total = gaussian_filter(np.where(filled, per_bin, 0.0), smooth, mode='constant')
        weight = gaussian_filter(filled.astype(float), smooth, mode='constant')
        return np.where(weight >= 0.5, total / weight, np.nan)
