function p = esc_paths(name, file_name)
%ESC_PATHS  Where the data are (MATLAB version of Tools/esc_paths.py).
%
%   esc_paths()                     <repository>/data
%   esc_paths('root')               the repository root
%   esc_paths('OTO-paired')         <repository>/data/OTO-paired, created if it does not exist yet
%   esc_paths('file', file_name)    full path of a data file, found by its name anywhere under data/
%
%   Generators write into esc_paths('<experiment>'); the validation script reads with
%   esc_paths('file', ...). The sweep scripts add this folder to the path with
%   addpath(fullfile(fileparts(mfilename('fullpath')), '..', 'Tools')).

root = fileparts(fileparts(mfilename('fullpath')));
data = fullfile(root, 'data');
if nargin == 0
    p = data;
elseif strcmp(name, 'root')
    p = root;
elseif strcmp(name, 'file')
    found = dir(fullfile(data, '**', file_name));
    if isempty(found)
        error('esc_paths:notFound', '%s not found under %s', file_name, data);
    elseif numel(found) > 1
        error('esc_paths:notUnique', '%s exists more than once under %s', file_name, data);
    end
    p = fullfile(found(1).folder, found(1).name);
else
    p = fullfile(data, name);
    if ~isfolder(p)
        mkdir(p);
    end
end
end
