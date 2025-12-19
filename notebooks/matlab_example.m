%% Poelis SDK - MATLAB Integration Example
% This script demonstrates how to use the Poelis Python SDK from MATLAB

%% Summary

fprintf('=== Summary ===\n');
fprintf('The PoelisMatlab facade provides:\n');
fprintf('  - Simple path-based API: pm.get_value("workspace.product.item.property")\n');
fprintf('  - Exploration: pm.list_children(path), pm.list_properties(path)\n');
fprintf('  - MATLAB-compatible types: all values are native Python types\n');
fprintf('  - Clear error messages for debugging\n');
fprintf('\n');

%% Setup: Initialize the Poelis MATLAB Facade
% TODO: Replace with your actual Python venv path
% TODO: Replace 'your-api-key' with your actual API key from: Organization Settings → API Keys in the Poelis webapp

pyenv('Version', '/path/to/python/venv/bin/python', 'ExecutionMode','OutOfProcess'); % TODO: Replace with your actual Python venv path

poelis_sdk = py.importlib.import_module('poelis_sdk');
pkg = py.importlib.import_module('pkg_resources');
disp(['poelis-sdk version: ' char(pkg.get_distribution('poelis-sdk').version)]);

api_key = 'your-api-key'; % TODO: Replace with your actual API key
pm = py.poelis_sdk.PoelisMatlab(api_key);
fprintf('✓ Poelis MATLAB facade initialized\n\n');

%% Example 1: List Available Workspaces

fprintf('=== Example 1: Listing Workspaces ===\n');
workspaces_py = pm.list_children();
workspaces = string(cell(workspaces_py));
fprintf('Available workspaces:\n');
for i = 1:length(workspaces)
    fprintf('  - %s\n', workspaces(i));
end
fprintf('\n');

%% Example 2: Get a Single Property Value

fprintf('=== Example 2: Getting a Property Value ===\n');
% Get the property value (returns Python float/int/str)
path = 'demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass';
value = pm.get_value(path);
% Convert to MATLAB double (for numeric values)
numeric_value = double(value);
fprintf('Property path: %s\n', path);
fprintf('Value: %.2f\n', numeric_value);
fprintf('Type: %s\n', class(numeric_value));
fprintf('\n');

%% Example 3: Get Property Information (Value, Unit, Category)

fprintf('=== Example 3b: Getting Property Information ===\n');
mass = pm.get_property('demo_workspace.demo_product.demo_item.demo_sub_item.demo_property_mass');
value = double(mass{'value'});
unit = char(mass{'unit'});
category = char(mass{'category'});
name = char(mass{'name'});

fprintf('Property: %s\n', name);
fprintf('Value: %.2f %s\n', value, unit);
fprintf('Category: %s\n', category);
fprintf('\n');

%% Example 4: Explore Available Nodes

fprintf('=== Example 4: Exploring Available Nodes ===\n');

% Replace with your actual workspace, product, and item names
workspace_name = 'demo_workspace';
product_name = 'demo_product';
item_name = 'demo_item';

% List products in workspace
fprintf('Listing products in workspace: %s\n', workspace_name);
products_py = pm.list_children(char(workspace_name));
products = string(cell(products_py));
fprintf('Products: %s\n', strjoin(products, ', '));
fprintf('\n');

% List items in product (path automatically resolves through baseline)
fprintf('Listing items in product: %s.%s\n', workspace_name, product_name);
item_path = [char(workspace_name), '.', char(product_name)];
items_py = pm.list_children(item_path);
items = string(cell(items_py));
fprintf('Items: %s\n', strjoin(items, ', '));
fprintf('\n');

% List properties of a specific item (path automatically resolves through baseline)
fprintf('Listing properties of item: %s.%s.%s\n', workspace_name, product_name, item_name);
full_item_path = [char(workspace_name), '.', char(product_name), '.', char(item_name)];
properties_py = pm.list_properties(char(full_item_path));
properties = string(cell(properties_py));
fprintf('Properties: %s\n', strjoin(properties, ', '));
fprintf('\n');

%% Example 5: Working with Versioned Products
% Access properties from specific product versions

fprintf('=== Example 5: Accessing Versioned Properties ===\n');

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

fprintf('\n');


