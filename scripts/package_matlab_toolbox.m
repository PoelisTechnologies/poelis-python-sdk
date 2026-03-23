function outputFile = package_matlab_toolbox()
%PACKAGE_MATLAB_TOOLBOX Build the Poelis MATLAB toolbox (.mltbx).
%   outputFile = PACKAGE_MATLAB_TOOLBOX() validates that the toolbox
%   metadata in src/poelis_matlab/toolbox.prj matches pyproject.toml and
%   then packages the toolbox into dist/PoelisToolbox-<version>.mltbx.

scriptDir = fileparts(mfilename("fullpath"));
repoRoot = fileparts(scriptDir);
toolboxRoot = fullfile(repoRoot, "src", "poelis_matlab");
toolboxProject = fullfile(toolboxRoot, "toolbox.prj");
pyprojectFile = fullfile(repoRoot, "pyproject.toml");
distDir = fullfile(repoRoot, "dist");

toolboxMetadata = localReadToolboxMetadata(toolboxProject);
pythonVersion = localReadPyprojectVersion(pyprojectFile);

if toolboxMetadata.version ~= pythonVersion
    error( ...
        "poelis:ToolboxVersionMismatch", ...
        "toolbox.prj version (%s) does not match pyproject.toml version (%s).", ...
        toolboxMetadata.version, ...
        pythonVersion);
end

if ~exist(distDir, "dir")
    mkdir(distDir);
end

toolboxFiles = localReadToolboxFiles(toolboxProject, toolboxRoot);

opts = matlab.addons.toolbox.ToolboxOptions(toolboxRoot, ...
    "109f0567-640f-40d7-aba5-c175ace7f2fc");
opts.ToolboxName = toolboxMetadata.name;
opts.ToolboxVersion = toolboxMetadata.version;
opts.AuthorName = toolboxMetadata.author;
opts.AuthorEmail = toolboxMetadata.email;
opts.AuthorCompany = toolboxMetadata.company;
opts.Summary = toolboxMetadata.summary;
opts.Description = toolboxMetadata.description;
opts.ToolboxImageFile = fullfile(toolboxRoot, "poelis-logo.png");
opts.ToolboxGettingStartedGuide = fullfile(toolboxRoot, "try_poelis_matlab.m");
opts.ToolboxFiles = toolboxFiles;
opts.ToolboxMatlabPath = {toolboxRoot};
opts.MinimumMatlabRelease = "R2018b";
opts.MaximumMatlabRelease = "";
opts.SupportedPlatforms = struct( ...
    "Glnxa64", true, ...
    "Maci64", true, ...
    "MatlabOnline", true, ...
    "Win64", true);
opts.OutputFile = fullfile(distDir, ...
    "PoelisToolbox-" + toolboxMetadata.version + ".mltbx");

matlab.addons.toolbox.packageToolbox(opts);
outputFile = string(opts.OutputFile);
fprintf("Packaged toolbox: %s\n", outputFile);
end

function metadata = localReadToolboxMetadata(projectFile)
text = fileread(projectFile);
metadata = struct( ...
    "name", localExtractXmlTag(text, "name"), ...
    "version", localExtractXmlTag(text, "version"), ...
    "author", localExtractXmlTag(text, "author"), ...
    "email", localExtractXmlTag(text, "email"), ...
    "company", localExtractXmlTag(text, "company"), ...
    "summary", localExtractXmlTag(text, "summary"), ...
    "description", localExtractXmlTag(text, "description"));
end

function value = localExtractXmlTag(text, tagName)
pattern = "<" + tagName + ">([\s\S]*?)</" + tagName + ">";
token = regexp(text, char(pattern), "tokens", "once");
if isempty(token)
    error("poelis:MissingToolboxMetadata", ...
        "Could not find <%s> in toolbox.prj.", tagName);
end

value = string(strtrim(token{1}));
end

function version = localReadPyprojectVersion(pyprojectFile)
text = fileread(pyprojectFile);
token = regexp(text, '^\s*version\s*=\s*"([^"]+)"\s*$', ...
    "tokens", "once", "lineanchors");
if isempty(token)
    error("poelis:MissingPyprojectVersion", ...
        "Could not find project.version in pyproject.toml.");
end

version = string(token{1});
end

function files = localReadToolboxFiles(projectFile, toolboxRoot)
text = fileread(projectFile);
tokens = regexp(text, "<file>(.*?)</file>", "tokens");
if isempty(tokens)
    error("poelis:MissingToolboxFiles", ...
        "Could not find any <file> entries in toolbox.prj.");
end

files = strings(numel(tokens), 1);
for idx = 1:numel(tokens)
    relativeFile = string(tokens{idx}{1});
    files(idx) = fullfile(toolboxRoot, relativeFile);
    if ~isfile(files(idx))
        error("poelis:MissingToolboxFile", ...
            "Toolbox file listed in toolbox.prj does not exist: %s", ...
            files(idx));
    end
end
end
