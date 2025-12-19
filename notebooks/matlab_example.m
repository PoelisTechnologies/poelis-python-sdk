%% Poelis SDK - MATLAB Integration Example
% This script demonstrates how to use the Poelis Python SDK from MATLAB
% using the PoelisMatlab facade class.
%
% Prerequisites:
%   1. Python >= 3.11 installed and accessible from MATLAB
%   2. Poelis SDK installed: pip install poelis-sdk
%   3. MATLAB configured to use your Python environment
%      (see: https://www.mathworks.com/help/matlab/call-python-libraries.html)
%
% Author: Poelis SDK Team
% Date: 2024

%% Setup: Initialize the Poelis MATLAB Facade
% Replace 'your-api-key' with your actual API key from:
% Organization Settings → API Keys in the Poelis webapp

api_key = 'your-api-key';  % TODO: Replace with your actual API key
pm = py.poelis_sdk.PoelisMatlab(api_key);

fprintf('✓ Poelis MATLAB facade initialized\n\n');

%% Example 1: List Available Workspaces
% Get a list of all workspaces you have access to
% Note: Use string() conversion to properly handle Python lists in MATLAB

fprintf('=== Example 1: Listing Workspaces ===\n');
workspaces_py = pm.list_children();
% Convert Python list to MATLAB string array (this prevents character-by-character iteration)
workspaces = string(cell(workspaces_py));
fprintf('Available workspaces:\n');
for i = 1:length(workspaces)
    fprintf('  - %s\n', workspaces(i));
end
fprintf('\n');

%% Example 2: Get a Single Property Value
% Access a property using dot-separated path notation
% Path format: workspace.product.item.property

fprintf('=== Example 2: Getting a Property Value ===\n');
try
    % Example path - adjust to match your actual workspace/product/item/property names
    path = 'demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass';
    
    % Get the property value (returns Python float/int/str)
    value = pm.get_value(path);
    
    % Convert to MATLAB double (for numeric values)
    numeric_value = double(value);
    
    fprintf('Property path: %s\n', path);
    fprintf('Value: %.2f\n', numeric_value);
    fprintf('Type: %s\n', class(numeric_value));
catch ME
    fprintf('Error: %s\n', ME.message);
    fprintf('Make sure the path exists in your Poelis instance.\n');
end
fprintf('\n');

%% Example 3: Get Multiple Properties at Once
% Use get_many() to fetch multiple properties efficiently
% Note: MATLAB cell arrays work directly with get_many()

fprintf('=== Example 3: Getting Multiple Properties ===\n');
try
    % Define multiple property paths as MATLAB cell array
    paths = {
        'demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass';
        'demo_workspace.demo_product.demo_item.prop_1';
        'demo_workspace.demo_product.demo_item.prop_2'
    };
    
    % Get all values at once
    values_dict = pm.get_many(paths);
    
    % Extract individual values
    % Note: Dictionary keys in MATLAB use curly braces
    mass = double(values_dict{'demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass'});
    color = char(values_dict{'demo_workspace.demo_product.demo_item.prop_1'});
    weight = double(values_dict{'demo_workspace.demo_product.demo_item.prop_2'});
    
    fprintf('Mass: %.2f\n', mass);
    fprintf('Color: %s\n', color);
    fprintf('Weight: %.2f\n', weight);
catch ME
    fprintf('Error: %s\n', ME.message);
end
fprintf('\n');

%% Example 3b: Get Property Information (Value, Unit, Category)
% Use get_property() to get property metadata along with the value

fprintf('=== Example 3b: Getting Property Information ===\n');
try
    % Get property info including value, unit, category, and name
    info = pm.get_property('demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass');
    
    % Extract information from the dictionary
    value = double(info{'value'});
    unit = char(info{'unit'});
    category = char(info{'category'});
    name = char(info{'name'});
    
    fprintf('Property: %s\n', name);
    fprintf('Value: %.2f %s\n', value, unit);
    fprintf('Category: %s\n', category);
catch ME
    fprintf('Error: %s\n', ME.message);
end
fprintf('\n');

%% Example 4: Explore Available Nodes
% List children at different levels to discover available data

fprintf('=== Example 4: Exploring Available Nodes ===\n');
try
    % List workspaces (root level)
    workspaces_py = pm.list_children();
    workspaces = string(cell(workspaces_py));
    if ~isempty(workspaces)
        workspace_name = workspaces(1);  % Use first workspace
        fprintf('Exploring workspace: %s\n', workspace_name);
        
        % List products in workspace
        products_py = pm.list_children(char(workspace_name));
        products = string(cell(products_py));
        fprintf('  Products: %s\n', strjoin(products, ', '));
        
        if ~isempty(products)
            product_name = products(1);  % Use first product
            full_product_path = [char(workspace_name), '.', char(product_name)];
            
            % List items in product
            items_py = pm.list_children(full_product_path);
            items = string(cell(items_py));
            fprintf('  Items: %s\n', strjoin(items, ', '));
        end
    end
catch ME
    fprintf('Error: %s\n', ME.message);
end
fprintf('\n');

%% Example 5: List Available Properties
% Get a list of all properties available at a specific item

fprintf('=== Example 5: Listing Available Properties ===\n');
try
    % Path to an item (adjust to match your data)
    item_path = 'demo_workspace.demo_product.demo_item';
    
    % List all properties (use string() conversion for proper handling)
    properties_py = pm.list_properties(item_path);
    properties = string(cell(properties_py));
    
    fprintf('Properties available at: %s\n', item_path);
    for i = 1:length(properties)
        fprintf('  - %s\n', properties(i));
    end
catch ME
    fprintf('Error: %s\n', ME.message);
    fprintf('Make sure the item path exists.\n');
end
fprintf('\n');

%% Example 6: Working with Versioned Products
% Access properties from specific product versions

fprintf('=== Example 6: Accessing Versioned Properties ===\n');
try
    % Access property from a specific version (v1, v2, etc.)
    version_path = 'demo_workspace.demo_product.v1.demo_item.demo_sub_item.demo_property_mass';
    value_v1 = double(pm.get_value(version_path));
    fprintf('Version 1 value: %.2f\n', value_v1);
    
    % Access property from baseline version
    baseline_path = 'demo_workspace.demo_product.baseline.demo_item.demo_sub_item.demo_property_mass';
    value_baseline = double(pm.get_value(baseline_path));
    fprintf('Baseline value: %.2f\n', value_baseline);
    
    % Access property from draft (current working version)
    draft_path = 'demo_workspace.demo_product.draft.demo_item.demo_sub_item.demo_property_mass';
    value_draft = double(pm.get_value(draft_path));
    fprintf('Draft value: %.2f\n', value_draft);
catch ME
    fprintf('Error: %s\n', ME.message);
    fprintf('Version paths require: workspace.product.vN.item.property\n');
end
fprintf('\n');

%% Example 7: Error Handling
% The facade provides clear error messages for debugging

fprintf('=== Example 7: Error Handling ===\n');
try
    % Try to access a non-existent property
    pm.get_value('nonexistent.workspace.product.property');
catch ME
    fprintf('Caught expected error:\n');
    fprintf('  Type: %s\n', class(ME));
    fprintf('  Message: %s\n', ME.message);
end
fprintf('\n');

%% Example 8: Type Conversion Tips
% Understanding return types and MATLAB conversion

fprintf('=== Example 8: Type Conversion ===\n');
try
    % Numeric properties return Python float/int
    numeric_path = 'demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass';
    numeric_value = pm.get_value(numeric_path);
    fprintf('Numeric value (Python type): %s\n', class(numeric_value));
    fprintf('Converted to MATLAB double: %.2f\n', double(numeric_value));
    
    % String properties return Python str
    string_path = 'demo_workspace.demo_product.demo_item.prop_1';
    string_value = pm.get_value(string_path);
    fprintf('String value (Python type): %s\n', class(string_value));
    fprintf('Converted to MATLAB char: %s\n', char(string_value));
    
    % Arrays/lists can be converted to MATLAB arrays
    % (if your properties return arrays)
catch ME
    fprintf('Error: %s\n', ME.message);
end
fprintf('\n');

%% Cleanup and Summary

fprintf('=== Summary ===\n');
fprintf('The PoelisMatlab facade provides:\n');
fprintf('  - Simple path-based API: pm.get_value("workspace.product.item.property")\n');
fprintf('  - Batch operations: pm.get_many([path1, path2, ...])\n');
fprintf('  - Exploration: pm.list_children(path), pm.list_properties(path)\n');
fprintf('  - MATLAB-compatible types: all values are native Python types\n');
fprintf('  - Clear error messages for debugging\n');
fprintf('\n');
fprintf('For more information, see README.md in the SDK repository.\n');

