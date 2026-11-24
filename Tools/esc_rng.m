function esc_rng(seed, skip)
%ESC_RNG  Start MATLAB's random stream as the sweep scripts do (Python: esc_sweeps.matlab_rng).
%
%   esc_rng(seed, skip)
%
%   seed = 0 : rng('default'), the stream of a freshly started MATLAB (Mersenne Twister, seed 0).
%              Python's esc_sweeps.matlab_rng(0) gives exactly the same numbers.
%   seed > 0 : rng(seed, 'twister'). Expected to match matlab_rng(seed) in Python (not checked).
%   skip     : number of random numbers to throw away first, to continue where an earlier sweep in
%              the same MATLAB session stopped (the values for the stored data sets are in the README).
%
%   See also ESC_DRAW.

if nargin < 2
    skip = 0;
end
if seed == 0
    rng('default');
else
    rng(seed, 'twister');
end
done = 0;
while done < skip                      % in blocks, to keep the memory use small
    block = min(skip - done, 1e6);
    rand(1, block);
    done = done + block;
end
end
