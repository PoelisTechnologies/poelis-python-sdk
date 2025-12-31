function [status, details] = checkInstallation()
    % checkInstallation - Check if Poelis Python SDK is properly installed
    %
    % Returns:
    %   status (logical): true if installation is OK, false otherwise
    %   details (struct): Detailed information about the installation
    %
    % Example:
    %   [ok, info] = poelis_sdk.checkInstallation();
    %   if ~ok
    %       fprintf('Installation check failed: %s\n', info.message);
    %   end
    
    details = struct();
    details.python_available = false;
    details.python_version = '';
    details.poelis_sdk_installed = false;
    details.poelis_sdk_version = '';
    details.message = '';
    
    % Check if Python is available
    try
        py_version = pyenv;
        if isempty(py_version.Version)
            details.message = 'Python environment not configured. Use pyenv(''Version'', ''/path/to/python'') to set it.';
            status = false;
            return;
        end
        details.python_available = true;
        details.python_version = char(py_version.Version);
    catch ME
        details.message = sprintf('Python not available: %s', ME.message);
        status = false;
        return;
    end
    
    % Check if poelis_sdk module can be imported
    try
        poelis_sdk = py.importlib.import_module('poelis_sdk');
        details.poelis_sdk_installed = true;
        
        % Try to get version
        try
            pkg = py.importlib.import_module('pkg_resources');
            dist = pkg.get_distribution('poelis-sdk');
            details.poelis_sdk_version = char(dist.version);
        catch
            details.poelis_sdk_version = 'unknown';
        end
    catch ME
        details.message = sprintf('poelis-sdk Python package not found. Install it with: pip install poelis-sdk\nOriginal error: %s', ME.message);
        status = false;
        return;
    end
    
    % All checks passed
    details.message = 'Installation OK';
    status = true;
    
    % Display summary
    if nargout == 0
        fprintf('Poelis Installation Check\n');
        fprintf('========================\n');
        fprintf('Python Available: %s\n', mat2str(details.python_available));
        if details.python_available
            fprintf('Python Version: %s\n', details.python_version);
        end
        fprintf('Poelis SDK Installed: %s\n', mat2str(details.poelis_sdk_installed));
        if details.poelis_sdk_installed
            fprintf('Poelis SDK Version: %s\n', details.poelis_sdk_version);
        end
        fprintf('Status: %s\n', details.message);
        fprintf('========================\n');
    end
end

