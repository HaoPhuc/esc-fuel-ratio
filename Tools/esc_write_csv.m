function esc_write_csv(filename, names, columns)
%ESC_WRITE_CSV  Write result columns to a CSV file, formatted as the Python sweep scripts do.
%
%   esc_write_csv(filename, names, columns)
%
%   names   : cell array of column names (the header line)
%   columns : cell array of the same length; each entry is a numeric or logical vector (one value
%             per row), a scalar (repeated on every row), a cell array of texts, or one text
%             (repeated on every row).
%   Numbers are written with 15 significant digits (like writetable and esc_sweeps.write_csv),
%   true/false as 1/0 and missing values as NaN.
%
%   See also ESC_SIM.

n_rows = 1;
for j = 1:numel(columns)
    c = columns{j};
    if ~(ischar(c) || (isstring(c) && isscalar(c)))
        n_rows = max(n_rows, numel(c));
    end
end

cells = cell(n_rows, numel(columns));
formats = cell(1, numel(columns));
for j = 1:numel(columns)
    c = columns{j};
    if ischar(c) || (isstring(c) && isscalar(c))      % one text for every row
        cells(:, j) = {char(c)};
        formats{j} = '%s';
    elseif iscell(c) || isstring(c)                   % one text per row
        cells(:, j) = cellstr(c(:));
        formats{j} = '%s';
    else                                              % numbers
        c = double(c(:));
        if isscalar(c)
            c = repmat(c, n_rows, 1);
        end
        cells(:, j) = num2cell(c);
        formats{j} = '%.15g';
    end
end

fid = fopen(filename, 'w');
if fid < 0
    error('esc_write_csv:open', 'Cannot open %s for writing.', filename);
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%s\n', strjoin(names, ','));
row_format = [strjoin(formats, ','), '\n'];
cells = cells';
fprintf(fid, row_format, cells{:});
fprintf('%d rows written to %s\n', n_rows, filename);
end
