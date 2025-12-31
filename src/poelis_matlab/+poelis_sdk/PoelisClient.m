classdef PoelisClient < handle
    % PoelisClient - MATLAB wrapper for Poelis Python SDK
    %
    % This class provides a MATLAB-friendly interface to the Poelis Python SDK.
    % All conversions between Python and MATLAB types are handled automatically.
    %
    % Usage:
    %   client = poelis_sdk.PoelisClient('your-api-key');
    %   workspaces = client.list_children();  % Returns string array directly
    %   value = client.get_value('workspace.product.property');  % Returns MATLAB double/string
    %
    % Properties:
    %   pm - Internal Python PoelisMatlab object (read-only)
    %
    % Methods:
    %   get_value(path) - Get property value by path
    %   get_property(path) - Get property info (value, unit, category, name
    %   change_property(path, value, title, description) - Update property value
    %   list_children(path) - List child nodes (returns string array)
    %   list_properties(path) - List property names (returns string array)
    
    properties (SetAccess = private)
        pm  % Python PoelisMatlab object
    end
    
    methods
        function obj = PoelisClient(api_key, base_url, timeout_seconds)
            % PoelisClient - Constructor
            %
            % Args:
            %   api_key (string, required): API key for Poelis API authentication
            %   base_url (string, optional): Base URL of the Poelis API. 
            %       Default: 'https://poelis-be-py-753618215333.europe-west1.run.app'
            %   timeout_seconds (double, optional): Network timeout in seconds.
            %       Default: 30.0
            %
            % Example:
            %   client = poelis_sdk.PoelisClient('your-api-key');
            %   client = poelis_sdk.PoelisClient('your-api-key', 'https://custom-url.com', 60.0);
            
            % Import the Python module
            try
                poelis_sdk = py.importlib.import_module('poelis_sdk');
            catch ME
                error('poelis:PythonModuleNotFound', ...
                    'Failed to import poelis_sdk Python module. Make sure the poelis-sdk package is installed in your Python environment.\nOriginal error: %s', ...
                    ME.message);
            end
            
            % Create Python PoelisMatlab object
            if nargin < 2
                base_url = 'https://poelis-be-py-753618215333.europe-west1.run.app';
            end
            if nargin < 3
                timeout_seconds = 30.0;
            end
            
            try
                obj.pm = poelis_sdk.PoelisMatlab(api_key, base_url, timeout_seconds);
            catch ME
                error('poelis:InitializationFailed', ...
                    'Failed to initialize PoelisMatlab. Check your API key and network connection.\nOriginal error: %s', ...
                    ME.message);
            end
        end
        
        function value = get_value(obj, path)
            % get_value - Get a property value by dot-separated path
            %
            % Args:
            %   path (string): Dot-separated path to the property, e.g.,
            %       'workspace.product.property' or 'workspace.product.v4.property'
            %
            % Returns:
            %   value: The property value as a MATLAB type (double, string, logical, etc.)
            %
            % Example:
            %   value = client.get_value('demo_workspace.demo_product.demo_property_mass');
            %   % Returns: 10.5 (as double)
            
            if ~ischar(path) && ~isstring(path)
                error('poelis:InvalidPath', 'Path must be a string or char array');
            end
            
            try
                py_value = obj.pm.get_value(char(path));
                value = poelis_sdk.PoelisClient.convertToMatlab(py_value);
            catch ME
                if contains(ME.message, 'Path cannot be empty')
                    error('poelis:EmptyPath', 'Path cannot be empty');
                elseif contains(ME.message, 'not found')
                    error('poelis:PathNotFound', 'Path not found: %s', path);
                else
                    error('poelis:GetValueFailed', ...
                        'Failed to get value at path "%s".\nOriginal error: %s', ...
                        path, ME.message);
                end
            end
        end
        
        function info = get_property(obj, path)
            % get_property - Get property information including value, unit, category, and name
            %
            % Args:
            %   path (string): Dot-separated path to the property, e.g.,
            %       'workspace.product.item.property'
            %
            % Returns:
            %   info (struct): Structure with fields:
            %       - value: Property value (double, string, logical, etc.)
            %       - unit: Unit string (or empty if not available)
            %       - category: Category string (or empty if not available)
            %       - name: Property name (or empty if not available)
            %
            % Example:
            %   info = client.get_property('workspace.product.item.property');
            %   fprintf('Value: %.2f %s\n', info.value, info.unit);
            
            if ~ischar(path) && ~isstring(path)
                error('poelis:InvalidPath', 'Path must be a string or char array');
            end
            
            try
                py_info = obj.pm.get_property(char(path));
                info = struct();
                info.value = poelis_sdk.PoelisClient.convertToMatlab(py_info{'value'});
                info.unit = poelis_sdk.PoelisClient.convertToMatlab(py_info{'unit'});
                info.category = poelis_sdk.PoelisClient.convertToMatlab(py_info{'category'});
                info.name = poelis_sdk.PoelisClient.convertToMatlab(py_info{'name'});
            catch ME
                if contains(ME.message, 'Path cannot be empty')
                    error('poelis:EmptyPath', 'Path cannot be empty');
                elseif contains(ME.message, 'not found')
                    error('poelis:PathNotFound', 'Path not found: %s', path);
                else
                    error('poelis:GetPropertyFailed', ...
                        'Failed to get property at path "%s".\nOriginal error: %s', ...
                        path, ME.message);
                end
            end
        end
        
        function children = list_children(obj, path)
            % list_children - List child node names at the given path
            %
            % Args:
            %   path (string, optional): Dot-separated path to the node whose children to list.
            %       If empty or omitted, lists workspaces at the root level.
            %
            % Returns:
            %   children (string array): Array of child node names
            %
            % Example:
            %   workspaces = client.list_children();  % List all workspaces
            %   products = client.list_children('demo_workspace');  % List products in workspace
            %   items = client.list_children('demo_workspace.demo_product');  % List items
            
            if nargin < 2 || isempty(path)
                path = '';
            end
            
            if ~ischar(path) && ~isstring(path)
                error('poelis:InvalidPath', 'Path must be a string or char array');
            end
            
            try
                py_children = obj.pm.list_children(char(path));
                children = poelis_sdk.PoelisClient.convertListToStringArray(py_children);
            catch ME
                if contains(ME.message, 'not found')
                    error('poelis:PathNotFound', 'Path not found: %s', path);
                else
                    error('poelis:ListChildrenFailed', ...
                        'Failed to list children at path "%s".\nOriginal error: %s', ...
                        path, ME.message);
                end
            end
        end
        
        function change_property(obj, path, value, title, description)
            % change_property - Update a property value by dot-separated path
            %
            % Args:
            %   path (string, required): Dot-separated path to the property, e.g.,
            %       'workspace.product.draft.item.property'
            %   value (required): New value for the property. Can be:
            %       - double: For numeric properties
            %       - string/char: For text, date, or status properties
            %       - array: For numeric array/matrix properties
            %   title (string, optional): Title/reason for history tracking
            %   description (string, optional): Description for history tracking
            %
            % Note: Only draft properties can be updated. Versioned properties
            %       (e.g., from v1, v2, baseline) cannot be changed.
            %
            % Example:
            %   % Update numeric property
            %   client.change_property('workspace.product.draft.item.mass', 123.45, 'Updated mass');
            %
            %   % Update text property
            %   client.change_property('workspace.product.draft.item.description', 'New text', 'Updated description');
            %
            %   % Update with title and description
            %   client.change_property('workspace.product.draft.item.mass', 123.45, ...
            %       'Updated mass', 'Changed mass value for testing');
            
            if nargin < 3
                error('poelis:InvalidArguments', 'change_property requires at least path and value arguments');
            end
            
            if ~ischar(path) && ~isstring(path)
                error('poelis:InvalidPath', 'Path must be a string or char array');
            end
            
            if isempty(path)
                error('poelis:EmptyPath', 'Path cannot be empty');
            end
            
            % Convert value to Python type
            py_value = poelis_sdk.PoelisClient.convertToPython(value);
            
            try
                if nargin >= 4 && ~isempty(title)
                    if ~ischar(title) && ~isstring(title)
                        error('poelis:InvalidTitle', 'Title must be a string or char array');
                    end
                    if nargin >= 5 && ~isempty(description)
                        if ~ischar(description) && ~isstring(description)
                            error('poelis:InvalidDescription', 'Description must be a string or char array');
                        end
                        % Call with both title and description
                        obj.pm.change_property(char(path), py_value, ...
                            pyargs('title', char(title), 'description', char(description)));
                    else
                        % Call with only title
                        obj.pm.change_property(char(path), py_value, ...
                            pyargs('title', char(title)));
                    end
                else
                    % Call without optional arguments
                    obj.pm.change_property(char(path), py_value);
                end
            catch ME
                if contains(ME.message, 'Path cannot be empty')
                    error('poelis:EmptyPath', 'Path cannot be empty');
                elseif contains(ME.message, 'not found')
                    error('poelis:PathNotFound', 'Path not found: %s', path);
                elseif contains(ME.message, 'Cannot update versioned property')
                    error('poelis:VersionedProperty', ...
                        'Cannot update versioned property. Only draft properties can be updated.\nPath: %s', ...
                        path);
                elseif contains(ME.message, 'Date must be in ISO 8601 format')
                    error('poelis:InvalidDate', ...
                        'Date value must be in ISO 8601 format (YYYY-MM-DD).\nPath: %s', ...
                        path);
                elseif contains(ME.message, 'Status must be one of')
                    error('poelis:InvalidStatus', ...
                        'Status value must be one of: DRAFT, UNDER_REVIEW, DONE.\nPath: %s', ...
                        path);
                else
                    error('poelis:ChangePropertyFailed', ...
                        'Failed to update property at path "%s".\nOriginal error: %s', ...
                        path, ME.message);
                end
            end
        end
        
        function properties = list_properties(obj, path)
            % list_properties - List property names available at the given path
            %
            % Args:
            %   path (string): Dot-separated path to an item, version, or product node.
            %       The path should end at a node that supports properties.
            %
            % Returns:
            %   properties (string array): Array of property names
            %
            % Example:
            %   props = client.list_properties('workspace.product.item');
            %   for i = 1:length(props)
            %       fprintf('Property: %s\n', props(i));
            %   end
            
            if ~ischar(path) && ~isstring(path)
                error('poelis:InvalidPath', 'Path must be a string or char array');
            end
            
            if isempty(path)
                error('poelis:EmptyPath', 'Path cannot be empty for list_properties');
            end
            
            try
                py_properties = obj.pm.list_properties(char(path));
                properties = poelis_sdk.PoelisClient.convertListToStringArray(py_properties);
            catch ME
                if contains(ME.message, 'not found')
                    error('poelis:PathNotFound', 'Path not found: %s', path);
                elseif contains(ME.message, 'does not support property listing')
                    error('poelis:UnsupportedNode', ...
                        'Node at path "%s" does not support property listing. Use an item, version, or product node.', ...
                        path);
                else
                    error('poelis:ListPropertiesFailed', ...
                        'Failed to list properties at path "%s".\nOriginal error: %s', ...
                        path, ME.message);
                end
            end
        end
    end
    
    methods (Static, Access = private)
        function matlab_value = convertToMatlab(py_value)
            % convertToMatlab - Convert Python value to MATLAB type
            %
            % Handles conversion of Python types to MATLAB types:
            %   - Python float/int -> MATLAB double
            %   - Python str -> MATLAB string
            %   - Python bool -> MATLAB logical
            %   - Python None -> MATLAB []
            %   - Python list -> MATLAB cell array or appropriate type
            %   - Python dict -> MATLAB struct
            
            % Handle None
            if isa(py_value, 'py.NoneType')
                matlab_value = [];
                return;
            end
            
            % Handle numeric types
            if isa(py_value, 'py.float') || isa(py_value, 'py.int')
                matlab_value = double(py_value);
                return;
            end
            
            % Handle boolean
            if isa(py_value, 'py.bool')
                matlab_value = logical(py_value);
                return;
            end
            
            % Handle string
            if isa(py_value, 'py.str')
                matlab_value = string(char(py_value));
                return;
            end
            
            % Handle list/tuple
            if isa(py_value, 'py.list') || isa(py_value, 'py.tuple')
                % Check if it's a list of strings (common case)
                try
                    cell_array = cell(py_value);
                    % Try to convert to string array if all elements are strings
                    all_strings = true;
                    for i = 1:length(cell_array)
                        if ~isa(cell_array{i}, 'py.str')
                            all_strings = false;
                            break;
                        end
                    end
                    if all_strings
                        str_array = strings(1, length(cell_array));
                        for i = 1:length(cell_array)
                            str_array(i) = string(char(cell_array{i}));
                        end
                        matlab_value = str_array;
                    else
                        % Mixed types - convert each element recursively
                        converted = cell(1, length(cell_array));
                        for i = 1:length(cell_array)
                            converted{i} = poelis_sdk.PoelisClient.convertToMatlab(cell_array{i});
                        end
                        matlab_value = converted;
                    end
                catch
                    % Fallback: return as cell array
                    matlab_value = cell(py_value);
                end
                return;
            end
            
            % Handle dict
            if isa(py_value, 'py.dict')
                try
                    keys = cell(py.list(py_value.keys()));
                    values = cell(py.list(py_value.values()));
                    s = struct();
                    for i = 1:length(keys)
                        key = char(keys{i});
                        % Replace invalid field name characters
                        key = matlab.lang.makeValidName(key);
                        s.(key) = poelis_sdk.PoelisClient.convertToMatlab(values{i});
                    end
                    matlab_value = s;
                catch
                    % Fallback: return as Python dict
                    matlab_value = py_value;
                end
                return;
            end
            
            % Default: try to convert to string, or return as-is
            try
                matlab_value = string(char(py_value));
            catch
                matlab_value = py_value;
            end
        end
        
        function str_array = convertListToStringArray(py_list)
            % convertListToStringArray - Convert Python list to MATLAB string array
            %
            % Specialized converter for lists of strings (common case for list_children
            % and list_properties)
            
            try
                cell_array = cell(py_list);
                str_array = strings(1, length(cell_array));
                for i = 1:length(cell_array)
                    if isa(cell_array{i}, 'py.str')
                        str_array(i) = string(char(cell_array{i}));
                    else
                        str_array(i) = string(char(cell_array{i}));
                    end
                end
            catch ME
                error('poelis:ConversionFailed', ...
                    'Failed to convert Python list to string array.\nOriginal error: %s', ...
                    ME.message);
            end
        end
        
        function py_value = convertToPython(matlab_value)
            % convertToPython - Convert MATLAB value to Python type
            %
            % Handles conversion of MATLAB types to Python types:
            %   - MATLAB double -> Python float
            %   - MATLAB string/char -> Python str
            %   - MATLAB logical -> Python bool
            %   - MATLAB numeric array -> Python list
            %   - MATLAB cell array -> Python list
            
            % Handle numeric types
            if isnumeric(matlab_value)
                if isscalar(matlab_value)
                    py_value = py.float(matlab_value);
                else
                    % Convert array to Python list
                    py_list = py.list();
                    for i = 1:numel(matlab_value)
                        py_list.append(py.float(matlab_value(i)));
                    end
                    py_value = py_list;
                end
                return;
            end
            
            % Handle string/char
            if ischar(matlab_value) || isstring(matlab_value)
                py_value = py.str(char(matlab_value));
                return;
            end
            
            % Handle logical
            if islogical(matlab_value)
                if isscalar(matlab_value)
                    py_value = py.bool(matlab_value);
                else
                    % Convert array to Python list
                    py_list = py.list();
                    for i = 1:numel(matlab_value)
                        py_list.append(py.bool(matlab_value(i)));
                    end
                    py_value = py_list;
                end
                return;
            end
            
            % Handle cell array
            if iscell(matlab_value)
                py_list = py.list();
                for i = 1:length(matlab_value)
                    converted = poelis_sdk.PoelisClient.convertToPython(matlab_value{i});
                    py_list.append(converted);
                end
                py_value = py_list;
                return;
            end
            
            % Default: try to convert to string
            try
                py_value = py.str(char(matlab_value));
            catch
                error('poelis:ConversionFailed', ...
                    'Cannot convert MATLAB value to Python type. Unsupported type: %s', ...
                    class(matlab_value));
            end
        end
    end
end

