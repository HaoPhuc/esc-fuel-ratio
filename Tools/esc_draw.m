function u = esc_draw(n_trials, n_calls)
%ESC_DRAW  Uniform random numbers for all trials, in the order of a trial-by-trial loop.
%
%   u = esc_draw(n_trials, n_calls)
%
%   Returns an n_trials x n_calls matrix. Row i holds the numbers that the i-th pass of a loop with
%   n_calls rand() calls per trial would get, in the order of the calls. This is the same as
%   esc_sweeps.draw() in Python, so both languages draw the same parameter sets.
%   (rand(n_calls, n_trials) fills column by column, i.e. trial by trial; the transpose puts one
%   trial per row.)
%
%   See also ESC_RNG.

u = rand(n_calls, n_trials)';
end
