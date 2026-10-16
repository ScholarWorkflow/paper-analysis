{
  description = "Nix delivery for the paper-analysis Codex skill (aarch64-darwin)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/6510408d147d8c5e6d76043e899e9251756f6a75";

    agent-env-nix = {
      url = "github:RekiDunois/agent-env-nix/2158e933aab6c845ae1ceb1228458d624f8777d5";
      inputs.nixpkgs.follows = "nixpkgs";
    };

    # base-skills declares its own nixpkgs and agent-env-nix pins; both follow
    # this repository's unified inputs so the installed vision-tools payload and
    # the vision-glance app come from one resolution context.
    base-skills = {
      url = "github:ScholarWorkflow/base-skills/3ab2ac188e625b8a8ae37b5fa318c579787c3d1e";
      inputs.nixpkgs.follows = "nixpkgs";
      inputs.agent-env-nix.follows = "agent-env-nix";
    };

    # Source-only: this flake imports nix/pdfx.nix directly with its own pkgs and
    # mkAgentPackage instead of consuming pdf-processing-core's flake outputs.
    pdf-processing-core = {
      url = "github:ScholarWorkflow/pdf-processing-core/3444dca0e0b84f46d1839ab5c707afa78e23d3a7";
      flake = false;
    };
  };

  outputs = { self, nixpkgs, agent-env-nix, base-skills, pdf-processing-core }:
    let
      system = "aarch64-darwin";
      pkgs = nixpkgs.legacyPackages.${system};
      mkAgentPackage = agent-env-nix.lib.mkAgentPackage;
      mkProject = agent-env-nix.lib.mkProject;

      pdfx = import "${pdf-processing-core}/nix/pdfx.nix" {
        inherit pkgs mkAgentPackage;
      };

      products = import ./nix/paper-analysis.nix {
        inherit pkgs mkAgentPackage mkProject pdfx;
        visionTools = base-skills.packages.${system}.vision-tools;
        visionGlanceProgram = base-skills.apps.${system}.vision-glance.program;
      };
    in
    {
      packages.${system} = {
        paper-analysis = products.package;
        paper-analysis-project = products.project;
        default = products.project;
      };
    };
}
