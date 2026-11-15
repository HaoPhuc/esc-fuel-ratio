%% Prerequisites
clc; clear all; close all;

%% Settings and background-calculations
% Time
dt = 0.01;

% Default ESC parameter values (same as in main.fuelratio.m)
default_dither_amplitude = 0.1;
default_dither_frequency = 0.1;
default_optimizer_gain   = 3e-4;
default_r_hat            = 0;

% Dynamics
n_D_decay_rate = 1/(1.71 + (rand()-0.5)*0.2); % +- 0.1
n_T_decay_rate = 1/(1.66 + (rand()-0.5)*0.2); % +- 0.1

% Density controller
proportional_gain = 3.129;
integral_gain = 2.482;
total_density_reference = 11.5; % e19 removed for numerical stability
greenwald_density_limit = 11.9; % e19 removed for numerical stability

% Ideal fuel ratio
ideal_ratio = n_T_decay_rate / (n_T_decay_rate + n_D_decay_rate);

% Calculate transfer function of dynamics and discretize
n_D_dynamics = ss(-n_D_decay_rate, 1, 1, 0);
n_T_dynamics = ss(-n_T_decay_rate, 1, 1, 0);
n_D_dynamics_discretized = c2d(n_D_dynamics, dt);
n_T_dynamics_discretized = c2d(n_T_dynamics, dt);
[Ad_D, Bd_D, ~, ~] = ssdata(n_D_dynamics_discretized);
[Ad_T, Bd_T, ~, ~] = ssdata(n_T_dynamics_discretized);

% Calculate initial steady state conditions
initial_ratio = 0.1;
initial_nD = 0.25 * (1-initial_ratio) * total_density_reference;
initial_nT = 0.25 * initial_ratio * total_density_reference;


%% Choosing mode: analyse or tune
% Analyse mode: Everything is constant except 1 variable to gain intuition.
% Tune mode: Using intuition gained from analyse mode to manually tune the simulation
mode = '';
while ~ismember(mode, {'analyse','tune'})
    mode = lower(strtrim(input('Analyse or tune? [analyse/tune]: ', 's')));
end

%% ========== ANALYSE MODE ==========
if strcmp(mode, 'analyse')

    % Choosing the variable
    valid_vars = {'dither_amplitude','dither_frequency','r_hat'};
    var_name = '';
    while ~ismember(var_name, valid_vars)
        var_name = strtrim(input('Choose one of the parameters as a variable: dither_amplitude / dither_frequency / r_hat:  ', 's'));
    end

    % The remaining two stay constant at their defaults
    params.dither_amplitude = default_dither_amplitude;
    params.dither_frequency = default_dither_frequency;
    params.r_hat            = default_r_hat;

    % Figure setup
    figure;
    subplot(1,3,1); h_Pt = plot(nan,nan,'b-'); hold on; xlabel('t'); ylabel('P'); title('P(t)'); grid on;
    subplot(1,3,2); h_Pr = plot(nan,nan,'b-'); hold on; xline(ideal_ratio,'c--'); xlabel('r'); ylabel('P'); title('P(r)'); grid on;
    subplot(1,3,3); h_rt = plot(nan,nan,'b-'); hold on; yline(ideal_ratio,'c--'); xlabel('t'); ylabel('r'); title('r(t)'); grid on;

    % Time and history
    t_total = 0;

    % Plant + PI controller states (persist across chunks)
    nD = initial_nD;
    nT = initial_nT;
    integral_density_error = 0;

    % Main loop
    running = true;
    while running
        % Adding time chunk
        chunk_duration = input('Chunk duration in seconds (Enter=5): ');
        if isempty(chunk_duration), chunk_duration = 5; end

        t_chunk = (t_total : dt : t_total + chunk_duration)'; % create a time vector
        n_steps = length(t_chunk); 
        P_chunk = nan(n_steps,1);
        r_chunk = nan(n_steps,1);
        
        dither_omega = params.dither_frequency * 2 * pi;
        for k = 1:n_steps
            t_current = t_chunk(k);
            r_current = params.r_hat + params.dither_amplitude * sin(dither_omega * t_current);
            r_current = min(max(r_current, 0), 1); % limit 0 < r_current < 1
            
            e_density = total_density_reference - (nD + nT); % density error
            integral_density_error = integral_density_error + e_density * dt; % total error over time
            S_total = proportional_gain*e_density + integral_gain*integral_density_error;
            S_total = max(S_total, 0);
            
            u_T = r_current * S_total;        % r is the TRITIUM fraction of the puff (D and T were swapped here before)
            u_D = (1 - r_current) * S_total;
            nD = Ad_D*nD + Bd_D*u_D;
            nT = Ad_T*nT + Bd_T*u_T;
            P = nD * nT;
            P_chunk(k) = P;
            r_chunk(k) = r_current;
        end
        
        t_hist = [];   % NOTE: the histories are reset for every chunk, so only the latest chunk is plotted; move these six lines above the loop to accumulate
        P_hist = [];
        r_hist = [];
        var_hist = [];
        P_avg_hist = [];
        r_avg_hist = [];
        t_hist = [t_hist; t_chunk];
        P_hist = [P_hist; P_chunk];
        r_hist = [r_hist; r_chunk];
        var_hist(end+1)   = params.(var_name);
        P_avg_hist(end+1) = mean(P_chunk, 'omitnan');
        r_avg_hist(end+1) = mean(r_chunk, 'omitnan');

        % Sort r and P for clean parabola
        [r_sorted, idx] = sort(r_hist);
        P_sorted = P_hist(idx);

        set(h_Pt, 'XData', t_hist,   'YData', P_hist);
        set(h_Pr, 'XData', r_sorted, 'YData', P_sorted);
        set(h_rt, 'XData', t_hist,   'YData', r_hist);

        subplot(1,3,1); axis tight;
        subplot(1,3,2); axis tight;
        subplot(1,3,3); axis tight;
        drawnow;

        t_total = t_total + chunk_duration;
        resp = input(sprintf('\nCurrent %s = %.4g\nEnter new value (Enter=keep, "q"=quit): ', var_name, params.(var_name)), 's');
        if strcmpi(resp, 'q')
            running = false;
        elseif ~isempty(resp)
            new_val = str2double(resp);
            if ~isnan(new_val)
                params.(var_name) = new_val;
            else
                disp('Could not parse — keeping previous value.');
            end
        end
    end

end
%% ========== TUNE MODE ==========
if strcmp(mode, 'tune')   % (this block used to run after analyse mode as well)

    dither_amplitude = default_dither_amplitude;
    dither_frequency = default_dither_frequency;
    optimizer_gain   = default_optimizer_gain;
    r_hat            = default_r_hat;

    dither_omega = dither_frequency * 2 * pi;
    highpass_cutoff_omega = dither_omega / pi;
    lowpass_cutoff_omega  = dither_omega / pi;
    highpass_filter_discretized = c2d(tf([1, 0], [1, highpass_cutoff_omega]), dt);
    lowpass_filter_discretized  = c2d(tf(lowpass_cutoff_omega, [1, lowpass_cutoff_omega]), dt);
    [num_hp, den_hp] = tfdata(highpass_filter_discretized, 'v');
    [num_lp, den_lp] = tfdata(lowpass_filter_discretized, 'v');
    zi_hp = zeros(max(length(num_hp),length(den_hp))-1,1);
    zi_lp = zeros(max(length(num_lp),length(den_lp))-1,1);

    nD = initial_nD;
    nT = initial_nT;
    integral_density_error = 0;

    t_total = 0;
    t_hist = []; P_hist = []; r_hist = [];

    figure;
    subplot(1,3,1); h_Pt = plot(nan,nan,'b-'); xlabel('t'); ylabel('P'); title('P(t)'); grid on;
    subplot(1,3,2); h_Pr = plot(nan,nan,'b-'); hold on; xline(ideal_ratio,'c--'); xlabel('r'); ylabel('P'); title('P(r)'); grid on;
    subplot(1,3,3); h_rt = plot(nan,nan,'b-'); hold on; yline(ideal_ratio,'c--'); xlabel('t'); ylabel('r'); title('r(t)'); grid on;

    running = true;
    while running

        chunk_duration = input('Chunk duration in seconds (Enter=5): ');
        if isempty(chunk_duration), chunk_duration = 5; end

        t_chunk = (t_total : dt : t_total + chunk_duration)';
        n_steps = length(t_chunk);
        P_chunk = nan(n_steps,1);
        r_chunk = nan(n_steps,1);

        for k = 1:n_steps
            t_current = t_chunk(k);

            r_current = r_hat + dither_amplitude * sin(dither_omega * t_current);
            r_current = min(max(r_current, 0), 1);

            e_density = total_density_reference - (nD + nT);
            integral_density_error = integral_density_error + e_density * dt;
            S_total = proportional_gain*e_density + integral_gain*integral_density_error;
            S_total = max(S_total, 0);

            u_T = r_current * S_total;        % r is the TRITIUM fraction of the puff (D and T were swapped here before)
            u_D = (1 - r_current) * S_total;

            nD = Ad_D*nD + Bd_D*u_D;
            nT = Ad_T*nT + Bd_T*u_T;

            P = nD * nT;

            [hp_out, zi_hp] = filter(num_hp, den_hp, P, zi_hp);
            demod = hp_out * (2/dither_amplitude) * sin(dither_omega * t_current);
            [xi, zi_lp] = filter(num_lp, den_lp, demod, zi_lp);

            r_hat = r_hat + optimizer_gain * xi * dt;
            r_hat = min(max(r_hat, 0), 1);

            P_chunk(k) = P;
            r_chunk(k) = r_current;
        end

        t_hist = [t_hist; t_chunk];
        P_hist = [P_hist; P_chunk];
        r_hist = [r_hist; r_chunk];

        set(h_Pt, 'XData', t_hist, 'YData', P_hist);
        set(h_Pr, 'XData', r_hist, 'YData', P_hist);
        set(h_rt, 'XData', t_hist, 'YData', r_hist);
        subplot(1,3,1); axis tight; subplot(1,3,2); axis tight; subplot(1,3,3); axis tight;
        drawnow;

        t_total = t_total + chunk_duration;

        resp = input(sprintf(['\nCurrent: amp=%.4g, freq=%.4g, gain=%.4g\n', ...
            'Enter new [amp freq gain] (Enter=keep, "q"=quit): '], ...
            dither_amplitude, dither_frequency, optimizer_gain), 's');

        if strcmpi(resp, 'q')
            running = false;
        elseif ~isempty(resp)
            vals = str2num(resp); %#ok<ST2NM>
            if numel(vals) == 3
                dither_amplitude = vals(1);
                new_frequency    = vals(2);
                optimizer_gain   = vals(3);

                if new_frequency ~= dither_frequency
                    dither_frequency = new_frequency;
                    dither_omega = dither_frequency * 2 * pi;
                    highpass_cutoff_omega = dither_omega / pi;
                    lowpass_cutoff_omega  = dither_omega / pi;
                    highpass_filter_discretized = c2d(tf([1, 0], [1, highpass_cutoff_omega]), dt);
                    lowpass_filter_discretized  = c2d(tf(lowpass_cutoff_omega, [1, lowpass_cutoff_omega]), dt);
                    [num_hp, den_hp] = tfdata(highpass_filter_discretized, 'v');
                    [num_lp, den_lp] = tfdata(lowpass_filter_discretized, 'v');
                    zi_hp = zeros(max(length(num_hp),length(den_hp))-1,1);
                    zi_lp = zeros(max(length(num_lp),length(den_lp))-1,1);
                end
            else
                disp('Could not parse — keeping previous values.');
            end
        end
    end

end % tune mode
