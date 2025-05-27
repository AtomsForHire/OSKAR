import yaml
import shlex
import os
import itertools
import copy
from pathlib import Path
import configparser
import subprocess
import datetime


def run_oskar_sim_interf(
    executable_path: str, ini_file_path: Path, cwd_path: Path, is_dry_run: bool
) -> bool:
    """
    Runs the OSKAR interferometer simulation using subprocess and logs its output.

    Args:
        executable_path: The command or path to the oskar_sim_interferometer executable.
        ini_file_path: Path object for the INI file.
        cwd_path: Path object for the directory from which to run the command AND store run.log.
        is_dry_run: If True, prints the command instead of running it and logs appropriately.

    Returns:
        True if the simulation was successful (or if dry_run is True and INI exists), False otherwise.
    """
    log_file_path = (
        cwd_path / "run.log"
    )  # Log file will be in the specific run's directory

    # Ensure the ini_file_path for the command is absolute for clarity in logs and execution
    # OSKAR itself might resolve relative paths from its CWD, but absolute is safer for the command list.
    # However, if the INI file contains paths relative to itself, running OSKAR with CWD set to
    # the INI's directory is key. We'll pass the INI path as given (could be relative to CWD).
    command = [
        executable_path,
        str(ini_file_path),
    ]  # OSKAR usually run with INI relative to CWD

    # For display/logging purposes, show how it would be run from CWD
    # Using shlex.quote for robustness if paths have spaces (though less common here)
    shell_like_command_display = (
        f"{shlex.quote(executable_path)} {shlex.quote(str(ini_file_path))}"
    )

    try:
        with open(log_file_path, "a") as log_f:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_f.write(
                f"--- Attempting OSKAR Interferometer simulation at {current_time} ---\n"
            )
            log_f.write(f"Run Directory (CWD): {cwd_path.resolve()}\n")
            log_f.write(
                f"INI File: {ini_file_path.resolve() if ini_file_path.is_absolute() else cwd_path / ini_file_path}\n"
            )  # Log resolved INI path
            log_f.write(
                f"Command to be executed in CWD: {shell_like_command_display}\n\n"
            )

            if (
                not ini_file_path.exists()
            ):  # Check this after attempting to log its intended path
                error_msg = (
                    f"    ERROR: Interferometer INI file not found at {ini_file_path}"
                )
                print(error_msg)
                log_f.write(f"ERROR: {error_msg}\n")
                log_f.write("--- Simulation Not Started ---\n\n")
                return False

            if is_dry_run:
                dry_run_msg = f"    [DRY RUN] Would execute: {shell_like_command_display} (from CWD: {cwd_path})"
                print(dry_run_msg)
                log_f.write("[DRY RUN] Command not executed.\n")
                log_f.write("--- Dry Run Concluded ---\n\n")
                return True

            print(f"    Executing OSKAR Interferometer simulation...")
            # Actual command uses paths as defined; CWD handles relativity for OSKAR
            process = subprocess.run(
                command,  # command uses ini_file_path as passed (could be relative to cwd_path)
                cwd=str(cwd_path),
                check=False,  # We'll check returncode manually to log output regardless
                capture_output=True,
                text=True,
            )

            log_f.write(f"Exit Code: {process.returncode}\n\n")

            log_f.write("--- Stdout ---\n")
            log_f.write(process.stdout if process.stdout.strip() else "<No stdout>\n")
            log_f.write("\n--- Stderr ---\n")
            log_f.write(process.stderr if process.stderr.strip() else "<No stderr>\n")

            if process.returncode == 0:
                success_msg = (
                    "    OSKAR Interferometer simulation finished successfully."
                )
                print(success_msg)
                log_f.write("\n--- Simulation Successful ---\n")
                # Optionally print summary of stdout/stderr to console for success
                if process.stdout.strip():
                    print(f"      (stdout logged to {log_file_path})")
                if process.stderr.strip():
                    print(f"      (stderr logged to {log_file_path})")
                return True
            else:
                error_msg_console = f"    ERROR: OSKAR Interferometer simulation failed with exit code {process.returncode}."
                print(error_msg_console)
                log_f.write(
                    f"\n!!! ERROR: Simulation Failed (Exit Code: {process.returncode}) !!!\n"
                )
                # Print full stdout/stderr to console on error for immediate visibility
                if process.stdout.strip():
                    print("    Stdout from error:")
                    print(process.stdout)
                if process.stderr.strip():
                    print("    Stderr from error:")
                    print(process.stderr)
                return False

    except FileNotFoundError:
        # This catches if executable_path itself is not found
        error_msg = f"    ERROR: Executable '{executable_path}' not found. Please check your PATH or configuration."
        print(error_msg)
        # Try to log to the file if possible, even if it's just this error
        try:
            with open(log_file_path, "a") as log_f_err:
                log_f_err.write(f"!!! FATAL ERROR: {error_msg} !!!\n")
                log_f_err.write("--- Simulation Not Started ---\n\n")
        except Exception:  # pylint: disable=broad-except
            pass  # If logging fails here, we've already printed to console
        return False
    except Exception as e:  # pylint: disable=broad-except
        # Catch any other unexpected errors during subprocess.run or logging
        error_msg = f"    ERROR: An unexpected error occurred: {e}"
        print(error_msg)
        try:
            with open(log_file_path, "a") as log_f_err:
                log_f_err.write(f"!!! UNEXPECTED FATAL ERROR: {error_msg} !!!\n")
                log_f_err.write("--- Simulation State Unknown ---\n\n")
        except Exception:  # pylint: disable=broad-except
            pass
        return False
    finally:
        # This block executes whether there was an exception or not,
        # but only if the initial `with open(log_file_path, 'a')` succeeded.
        # To ensure it always tries to log completion if the outer try was entered:
        try:
            with open(
                log_file_path, "a"
            ) as log_f_final:  # Re-open in case of early exit from try
                final_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_f_final.write(
                    f"--- Logging for this attempt concluded at {final_time} ---\n\n"
                )
        except Exception:  # pylint: disable=broad-except
            # If even final logging fails, there's not much more to do here
            pass


def run_oskar_sim_beam(
    executable_path: str, ini_file_path: Path, cwd_path: Path, is_dry_run: bool
) -> bool:
    """
    Runs the OSKAR beam pattern simulation using subprocess and logs its output.

    Args:
        executable_path: The command or path to the oskar_sim_beam_pattern executable.
        ini_file_path: Path object for the INI file.
        cwd_path: Path object for the directory from which to run the command AND store run.log.
        is_dry_run: If True, prints the command instead of running it and logs appropriately.

    Returns:
        True if the simulation was successful (or if dry_run is True and INI exists), False otherwise.
    """
    log_file_path = (
        cwd_path / "run.log"
    )  # Log file will be in the specific run's directory
    command = [
        executable_path,
        str(ini_file_path),
    ]
    shell_like_command_display = (
        f"{shlex.quote(executable_path)} {shlex.quote(str(ini_file_path))}"
    )

    try:
        # Open log file in append mode. New entries will be added.
        # If other steps (like INI generation) log to this file, they should also use append.
        with open(log_file_path, "a") as log_f:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_f.write(
                f"--- Attempting OSKAR Beam Pattern simulation at {current_time} ---\n"
            )
            log_f.write(f"Run Directory (CWD): {cwd_path.resolve()}\n")
            log_f.write(
                f"INI File: {ini_file_path.resolve() if ini_file_path.is_absolute() else cwd_path / ini_file_path}\n"
            )
            log_f.write(
                f"Command to be executed in CWD: {shell_like_command_display}\n\n"
            )

            if not ini_file_path.exists():
                error_msg = (
                    f"    ERROR: Beam Pattern INI file not found at {ini_file_path}"
                )
                print(error_msg)
                log_f.write(f"ERROR: {error_msg}\n")
                log_f.write("--- Simulation Not Started ---\n\n")
                return False

            if is_dry_run:
                dry_run_msg = f"    [DRY RUN] Would execute: {shell_like_command_display} (from CWD: {cwd_path})"
                print(dry_run_msg)
                log_f.write("[DRY RUN] Command not executed.\n")
                log_f.write("--- Dry Run Concluded ---\n\n")
                return True

            print(f"    Executing OSKAR Beam Pattern simulation...")
            process = subprocess.run(
                command,
                cwd=str(cwd_path),
                check=False,  # Check returncode manually to log output regardless
                capture_output=True,
                text=True,
            )

            log_f.write(f"Exit Code: {process.returncode}\n\n")

            log_f.write("--- Stdout ---\n")
            log_f.write(process.stdout if process.stdout.strip() else "<No stdout>\n")
            log_f.write("\n--- Stderr ---\n")
            log_f.write(process.stderr if process.stderr.strip() else "<No stderr>\n")

            if process.returncode == 0:
                success_msg = "    OSKAR Beam Pattern simulation finished successfully."
                print(success_msg)
                log_f.write("\n--- Simulation Successful ---\n")
                if process.stdout.strip():
                    print(f"      (stdout logged to {log_file_path})")
                if process.stderr.strip():
                    print(f"      (stderr logged to {log_file_path})")
                return True
            else:
                error_msg_console = f"    ERROR: OSKAR Beam Pattern simulation failed with exit code {process.returncode}."
                print(error_msg_console)
                log_f.write(
                    f"\n!!! ERROR: Simulation Failed (Exit Code: {process.returncode}) !!!\n"
                )
                if process.stdout.strip():
                    print("    Stdout from error:")
                    print(process.stdout)
                if process.stderr.strip():
                    print("    Stderr from error:")
                    print(process.stderr)
                return False

    except FileNotFoundError:
        error_msg = f"    ERROR: Executable '{executable_path}' not found. Please check your PATH or configuration."
        print(error_msg)
        try:
            with open(
                log_file_path, "a"
            ) as log_f_err:  # Attempt to log this critical failure too
                log_f_err.write(f"!!! FATAL ERROR: {error_msg} !!!\n")
                log_f_err.write("--- Simulation Not Started ---\n\n")
        except Exception:  # pylint: disable=broad-except
            pass
        return False
    except Exception as e:  # pylint: disable=broad-except
        error_msg = f"    ERROR: An unexpected error occurred while running OSKAR Beam Pattern: {e}"
        print(error_msg)
        try:
            with open(log_file_path, "a") as log_f_err:
                log_f_err.write(f"!!! UNEXPECTED FATAL ERROR: {error_msg} !!!\n")
                log_f_err.write("--- Simulation State Unknown ---\n\n")
        except Exception:  # pylint: disable=broad-except
            pass
        return False
    finally:
        try:
            with open(log_file_path, "a") as log_f_final:
                final_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_f_final.write(
                    f"--- Logging for this OSKAR Beam attempt concluded at {final_time} ---\n\n"
                )
        except Exception:  # pylint: disable=broad-except
            pass  # Final attempt to log, if it fails, not much else to do


def run_wsclean():
    pass


def run_calibrate(
    executable_path: str,
    hyperdrive_cfg: dict,
    global_output_cfg: dict,
    cwd_path: Path,
    is_dry_run: bool,
) -> bool:
    log_file_path = (
        cwd_path / "run.log"
    )  # Log file will be in the specific run's directory
    command = [
        executable_path,
        f"-d {global_output_cfg.get('interf_ms_base_filename', 'sim.ms')}",
        f"--source-list {hyperdrive_cfg.get('srclist', None)}",
        f"-o {hyperdrive_cfg.get('sol_output', 'hyperdrive_solutions.fits')}",
    ]
    shell_like_command_display = f"{shlex.quote(executable_path)} -d {global_output_cfg.get('interf_ms_base_filename', 'sim.ms')} --source-list {hyperdrive_cfg.get('srclist', None)} -o {hyperdrive_cfg.get('sol_output', 'hyperdrive_solutions.fits')}"

    try:
        with open(log_file_path, "a") as log_f:
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_f.write(f"--- Attempting Hyperdrive at {current_time} ---\n")
            log_f.write(f"Run Directory (CWD): {cwd_path.resolve()}\n")
            log_f.write(
                f"Command to be executed in CWD: {shell_like_command_display}\n\n"
            )

            if is_dry_run:
                dry_run_msg = f"    [DRY RUN] Would execute: {shell_like_command_display} (from CWD: {cwd_path})"
                print(dry_run_msg)
                log_f.write("[DRY RUN] Command not executed.\n")
                log_f.write("--- Dry Run Concluded ---\n\n")
                return True

            print(f"    Executing Hyperdrive calibration...")
            process = subprocess.run(
                command,
                cwd=str(cwd_path),
                check=False,  # Check returncode manually to log output regardless
                capture_output=True,
                text=True,
            )

            log_f.write(f"Exit Code: {process.returncode}\n\n")

            log_f.write("--- Stdout ---\n")
            log_f.write(process.stdout if process.stdout.strip() else "<No stdout>\n")
            log_f.write("\n--- Stderr ---\n")
            log_f.write(process.stderr if process.stderr.strip() else "<No stderr>\n")

            if process.returncode == 0:
                success_msg = "    Hyperdrive finished successfully."
                print(success_msg)
                log_f.write("\n--- Hyperdrive Successful ---\n")
                if process.stdout.strip():
                    print(f"      (stdout logged to {log_file_path})")
                if process.stderr.strip():
                    print(f"      (stderr logged to {log_file_path})")
                return True
            else:
                error_msg_console = (
                    f"    ERROR: Hyperdrive failed with exit code {process.returncode}."
                )
                print(error_msg_console)
                log_f.write(
                    f"\n!!! ERROR: Hyperdrive Failed (Exit Code: {process.returncode}) !!!\n"
                )
                if process.stdout.strip():
                    print("    Stdout from error:")
                    print(process.stdout)
                if process.stderr.strip():
                    print("    Stderr from error:")
                    print(process.stderr)
                return False

    except FileNotFoundError:
        error_msg = f"    ERROR: Executable '{executable_path}' not found. Please check your PATH or configuration."
        print(error_msg)
        try:
            with open(
                log_file_path, "a"
            ) as log_f_err:  # Attempt to log this critical failure too
                log_f_err.write(f"!!! FATAL ERROR: {error_msg} !!!\n")
                log_f_err.write("--- Simulation Not Started ---\n\n")
        except Exception:  # pylint: disable=broad-except
            pass
        return False
    except Exception as e:  # pylint: disable=broad-except
        error_msg = f"    ERROR: An unexpected error occurred while running OSKAR Beam Pattern: {e}"
        print(error_msg)
        try:
            with open(log_file_path, "a") as log_f_err:
                log_f_err.write(f"!!! UNEXPECTED FATAL ERROR: {error_msg} !!!\n")
                log_f_err.write("--- Simulation State Unknown ---\n\n")
        except Exception:  # pylint: disable=broad-except
            pass
        return False
    finally:
        try:
            with open(log_file_path, "a") as log_f_final:
                final_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_f_final.write(
                    f"--- Logging for this Hyperdrive attempt concluded at {final_time} ---\n\n"
                )
        except Exception:  # pylint: disable=broad-except
            pass  # Final attempt to log, if it fails, not much else to do


def _flatten_settings_for_configparser(settings_dict, prefix=""):
    """
    Recursively flattens a nested dictionary into OSKAR-style keys
    for use with configparser.
    Returns a flat dictionary where values are strings.
    """
    flat_dict = {}
    for key, value in settings_dict.items():
        if value is None:  # Skip None values explicitly
            continue

        oskar_key = f"{prefix}{key}"
        if isinstance(value, dict):
            # If the value is another dictionary, recurse
            flat_dict.update(_flatten_settings_for_configparser(value, f"{oskar_key}/"))
        elif isinstance(value, bool):
            # Convert Python bool to lowercase string 'true'/'false'
            flat_dict[oskar_key] = str(value).lower()
        else:
            # Ensure all values are strings for configparser
            flat_dict[oskar_key] = str(value)
    return flat_dict


def write_ini_file_with_configparser(ini_data_dict, output_path):
    """
    Generates an OSKAR-style INI file using configparser.
    ini_data_dict: A dictionary where top-level keys are section names and
                   their values are (potentially nested) dictionaries of settings.
    """
    config = configparser.ConfigParser()
    config.optionxform = str  # Preserve key case (OSKAR keys are case-sensitive)

    for section_name, settings_dict in ini_data_dict.items():
        if not isinstance(settings_dict, dict):
            print(
                f"# WARNING: Skipping section '{section_name}' as its value is not a dictionary."
            )
            continue

        # config.add_section(section_name) # Ensure section exists
        # flattened_settings = _flatten_settings_for_configparser(settings_dict)
        # for key, value in flattened_settings.items():
        #     config.set(section_name, key, value)

        # More direct way: assign the flattened dictionary to the section
        config[section_name] = _flatten_settings_for_configparser(settings_dict)

    with open(output_path, "w") as configfile:
        config.write(configfile)


def generate_beam_ini_data(
    oskar_ini_defaults: dict,
    current_tel_config: dict,
    current_pc_config: dict,
    global_run_settings: dict,
    global_output_config: dict,
    current_run_specific_output_dir: Path,  # e.g., Path("./simulation_outputs_python/images_...")
    project_root_path: Path,
) -> dict:
    """
    Generates the nested dictionary for an OSKAR beam simulation INI file.

    Args:
        oskar_ini_defaults: Dictionary from the 'oskar_ini_defaults' section of the master YAML.
        current_tel_config: Dictionary for the current telescope configuration.
        current_pc_config: Dictionary for the current phase centre configuration.
        global_run_settings: Dictionary from 'run_settings' (for include_telescope_errors).
        global_output_config: Dictionary from 'output_config' (for beam_root_path_base).
        current_run_specific_output_dir: Path object to the dedicated output directory for this run.
        project_root_path: Path object to the project's root directory (for resolving relative input paths).

    Returns:
        A dictionary structured for conversion to an OSKAR beam simulation INI file.
    """
    beam_ini_data = {}

    # 1. Deep copy common sections from oskar_ini_defaults
    for common_sec_name in ["General", "simulator", "observation", "telescope"]:
        if common_sec_name in oskar_ini_defaults:
            beam_ini_data[common_sec_name] = copy.deepcopy(
                oskar_ini_defaults[common_sec_name]
            )
        else:
            # Ensure section exists even if empty in defaults, so subsequent keys can be added
            beam_ini_data[common_sec_name] = {}

    # 2. Deep copy and merge sections from the beam_pattern_module
    beam_module_from_defaults = copy.deepcopy(
        oskar_ini_defaults.get("beam_pattern_module", {})
    )
    for (
        section_key_in_module,
        section_values_in_module,
    ) in beam_module_from_defaults.items():
        # section_key_in_module will typically be "beam_pattern"
        beam_ini_data[section_key_in_module] = section_values_in_module

    # 3. Populate/Override values in beam_ini_data

    # [General]
    beam_ini_data.setdefault("General", {})["app"] = "oskar_sim_beam_pattern"
    # 'version' would typically come from oskar_ini_defaults if set there, or hardcoded
    beam_ini_data["General"]["version"] = oskar_ini_defaults.get("General", {}).get(
        "version", "unknown"
    )

    # [simulator]
    sim_defaults = oskar_ini_defaults.get("simulator", {})
    sim_cfg = beam_ini_data.setdefault("simulator", {})
    sim_cfg["use_gpus"] = sim_defaults.get("use_gpus")
    sim_cfg["double_precision"] = sim_defaults.get("double_precision")

    # [observation]
    obs_cfg = beam_ini_data.setdefault("observation", {})
    obs_defaults = oskar_ini_defaults.get(
        "observation", {}
    )  # Get defaults for this section
    obs_cfg["phase_centre_ra_deg"] = current_pc_config["ra_deg"]
    obs_cfg["phase_centre_dec_deg"] = current_pc_config["dec_deg"]
    obs_cfg["start_time_utc"] = current_pc_config["start_time_utc"]
    obs_cfg["start_frequency_hz"] = obs_defaults.get("start_frequency_hz")
    obs_cfg["frequency_inc_hz"] = obs_defaults.get("frequency_inc_hz")
    obs_cfg["num_channels"] = obs_defaults.get("num_channels")
    obs_cfg["length"] = obs_defaults.get("length")  # maps to params.length_obs
    obs_cfg["num_time_steps"] = obs_defaults.get("num_time_steps")

    # [telescope]
    tel_cfg_sec = beam_ini_data.setdefault("telescope", {})
    tel_defaults = oskar_ini_defaults.get(
        "telescope", {}
    )  # Get defaults for this section

    # Resolve input_directory relative to the current run's output directory
    # Assuming oskar_input_directory in tel_config is relative to project_root_path
    tel_input_dir_abs = (
        project_root_path / current_tel_config["oskar_input_directory"]
    ).resolve()
    tel_cfg_sec["input_directory"] = os.path.relpath(
        tel_input_dir_abs, current_run_specific_output_dir
    )

    # Ensure nested structure for aperture_array and its sub-elements
    ap_array_cfg = tel_cfg_sec.setdefault("aperture_array", {})
    el_pattern_cfg = ap_array_cfg.setdefault("element_pattern", {})
    arr_pattern_el_cfg = ap_array_cfg.setdefault("array_pattern", {}).setdefault(
        "element", {}
    )

    # Get defaults for these nested structures
    el_pattern_defaults = tel_defaults.get("aperture_array", {}).get(
        "element_pattern", {}
    )
    arr_el_defaults = (
        tel_defaults.get("aperture_array", {})
        .get("array_pattern", {})
        .get("element", {})
    )

    el_pattern_cfg["enable_numerical"] = el_pattern_defaults.get(
        "enable_numerical", False
    )

    arr_pattern_el_cfg["x_gain"] = arr_el_defaults.get("x_gain")
    arr_pattern_el_cfg["y_gain"] = arr_el_defaults.get("y_gain")
    arr_pattern_el_cfg["x_phase_error_fixed_deg"] = arr_el_defaults.get(
        "x_phase_error_fixed_deg"
    )
    arr_pattern_el_cfg["y_phase_error_fixed_deg"] = arr_el_defaults.get(
        "y_phase_error_fixed_deg"
    )

    # Effective errors based on global flag and per-PC settings
    is_errors_globally_on = global_run_settings.get("include_telescope_errors", False)
    eff_gain_std = "0.0"
    eff_phase_std = "0.0"
    if is_errors_globally_on:
        eff_gain_std = current_pc_config.get("gain_error_std", "0.0")
        eff_phase_std = current_pc_config.get("phase_error_std", "0.0")

    arr_pattern_el_cfg["x_gain_error_time"] = eff_gain_std
    arr_pattern_el_cfg["y_gain_error_time"] = eff_gain_std
    arr_pattern_el_cfg["x_phase_error_time_deg"] = eff_phase_std
    arr_pattern_el_cfg["y_phase_error_time_deg"] = eff_phase_std

    # [beam_pattern] specific settings
    beam_pattern_cfg_sec = beam_ini_data.setdefault("beam_pattern", {})
    # Get defaults for this section (which came from beam_pattern_module)
    beam_pattern_module_defaults = oskar_ini_defaults.get(
        "beam_pattern_module", {}
    ).get("beam_pattern", {})

    beam_image_cfg = beam_pattern_cfg_sec.setdefault("beam_image", {})
    beam_image_defaults = beam_pattern_module_defaults.get("beam_image", {})
    beam_image_cfg["fov_deg"] = beam_image_defaults.get("fov_deg")

    # root_path is relative to the INI file's location (current_run_specific_output_dir)
    beam_pattern_cfg_sec["root_path"] = global_output_config.get(
        "beam_root_path_base", "beam_output_default"
    )

    station_outputs_cfg = beam_pattern_cfg_sec.setdefault(
        "station_outputs", {}
    ).setdefault("fits_image", {})
    station_outputs_defaults = beam_pattern_module_defaults.get(
        "station_outputs", {}
    ).get("fits_image", {})
    station_outputs_cfg["amp"] = station_outputs_defaults.get("amp", True)

    return beam_ini_data


def generate_interf_ini_data(
    oskar_ini_defaults: dict,
    current_tel_config: dict,
    current_sky_config: dict,  # Contains the 'filename' for the current sky model
    current_pc_config: dict,
    global_run_settings: dict,
    global_output_config: dict,
    sky_models_base_dir: str,  # Path string for the base directory of sky models
    current_run_specific_output_dir: Path,
    project_root_path: Path,
) -> dict:
    """
    Generates the nested dictionary for an OSKAR interferometer simulation INI file.

    Args:
        oskar_ini_defaults: Dictionary from 'oskar_ini_defaults' of the master YAML.
        current_tel_config: Dictionary for the current telescope configuration.
        current_sky_config: Dictionary for the current sky model configuration.
        current_pc_config: Dictionary for the current phase centre configuration.
        global_run_settings: Dictionary from 'run_settings'.
        global_output_config: Dictionary from 'output_config'.
        sky_models_base_dir: Base path string for sky model files.
        current_run_specific_output_dir: Path object to the output directory for this run.
        project_root_path: Path object to the project's root directory.

    Returns:
        A dictionary structured for an OSKAR interferometer INI file.
    """
    interf_ini_data = {}

    # 1. Deep copy common sections from oskar_ini_defaults
    for common_sec_name in ["General", "simulator", "observation", "telescope"]:
        if common_sec_name in oskar_ini_defaults:
            interf_ini_data[common_sec_name] = copy.deepcopy(
                oskar_ini_defaults[common_sec_name]
            )
        else:
            interf_ini_data[common_sec_name] = {}

    # 2. Deep copy and merge sections from the interferometer_module
    interf_module_from_defaults = copy.deepcopy(
        oskar_ini_defaults.get("interferometer_module", {})
    )
    for (
        section_key_in_module,
        section_values_in_module,
    ) in interf_module_from_defaults.items():
        # section_key_in_module will be "interferometer" or "sky"
        interf_ini_data[section_key_in_module] = section_values_in_module

    # 3. Populate/Override values in interf_ini_data

    # [General]
    interf_ini_data.setdefault("General", {})["app"] = "oskar_sim_interferometer"
    interf_ini_data["General"]["version"] = oskar_ini_defaults.get("General", {}).get(
        "version", "unknown"
    )

    # [simulator]
    sim_defaults = oskar_ini_defaults.get("simulator", {})
    sim_cfg = interf_ini_data.setdefault("simulator", {})
    sim_cfg["use_gpus"] = sim_defaults.get("use_gpus")
    sim_cfg["double_precision"] = sim_defaults.get("double_precision")

    # [observation]
    obs_cfg = interf_ini_data.setdefault("observation", {})
    obs_defaults = oskar_ini_defaults.get("observation", {})
    obs_cfg["phase_centre_ra_deg"] = current_pc_config["ra_deg"]
    obs_cfg["phase_centre_dec_deg"] = current_pc_config["dec_deg"]
    obs_cfg["start_time_utc"] = current_pc_config["start_time_utc"]
    obs_cfg["start_frequency_hz"] = obs_defaults.get("start_frequency_hz")
    obs_cfg["frequency_inc_hz"] = obs_defaults.get("frequency_inc_hz")
    obs_cfg["num_channels"] = obs_defaults.get("num_channels")
    obs_cfg["length"] = obs_defaults.get("length")  # maps to params.length_obs
    obs_cfg["num_time_steps"] = obs_defaults.get("num_time_steps")

    # [telescope]
    tel_cfg_sec = interf_ini_data.setdefault("telescope", {})
    tel_defaults = oskar_ini_defaults.get("telescope", {})

    tel_input_dir_abs = (
        project_root_path / current_tel_config["oskar_input_directory"]
    ).resolve()
    tel_cfg_sec["input_directory"] = os.path.relpath(
        tel_input_dir_abs, current_run_specific_output_dir
    )

    ap_array_cfg = tel_cfg_sec.setdefault("aperture_array", {})
    el_pattern_cfg = ap_array_cfg.setdefault("element_pattern", {})
    arr_pattern_el_cfg = ap_array_cfg.setdefault("array_pattern", {}).setdefault(
        "element", {}
    )

    el_pattern_defaults = tel_defaults.get("aperture_array", {}).get(
        "element_pattern", {}
    )
    arr_el_defaults = (
        tel_defaults.get("aperture_array", {})
        .get("array_pattern", {})
        .get("element", {})
    )

    el_pattern_cfg["enable_numerical"] = el_pattern_defaults.get(
        "enable_numerical", False
    )

    arr_pattern_el_cfg["x_gain"] = arr_el_defaults.get("x_gain")
    arr_pattern_el_cfg["y_gain"] = arr_el_defaults.get("y_gain")
    arr_pattern_el_cfg["x_phase_error_fixed_deg"] = arr_el_defaults.get(
        "x_phase_error_fixed_deg"
    )
    arr_pattern_el_cfg["y_phase_error_fixed_deg"] = arr_el_defaults.get(
        "y_phase_error_fixed_deg"
    )

    is_errors_globally_on = global_run_settings.get("include_telescope_errors", False)
    eff_gain_std = "0.0"
    eff_phase_std = "0.0"
    if is_errors_globally_on:
        eff_gain_std = current_pc_config.get("gain_error_std", "0.0")
        eff_phase_std = current_pc_config.get("phase_error_std", "0.0")

    arr_pattern_el_cfg["x_gain_error_time"] = eff_gain_std
    arr_pattern_el_cfg["y_gain_error_time"] = eff_gain_std
    arr_pattern_el_cfg["x_phase_error_time_deg"] = eff_phase_std
    arr_pattern_el_cfg["y_phase_error_time_deg"] = eff_phase_std

    # [interferometer] specific settings
    interf_sec_cfg = interf_ini_data.setdefault("interferometer", {})
    interf_module_defaults = oskar_ini_defaults.get("interferometer_module", {}).get(
        "interferometer", {}
    )  # Defaults for this section
    # ms_filename is relative to INI file location (current_run_specific_output_dir)
    interf_sec_cfg["ms_filename"] = global_output_config.get(
        "interf_ms_base_filename", "vis_default.ms"
    )
    interf_sec_cfg["channel_bandwidth_hz"] = interf_module_defaults.get(
        "channel_bandwidth_hz"
    )
    interf_sec_cfg["time_average_sec"] = interf_module_defaults.get("time_average_sec")

    # [sky] specific settings for interferometer
    sky_sec_cfg = interf_ini_data.setdefault("sky", {}).setdefault(
        "oskar_sky_model", {}
    )
    sky_module_defaults = (
        oskar_ini_defaults.get("interferometer_module", {})
        .get("sky", {})
        .get("oskar_sky_model", {})
    )  # Defaults

    sky_model_file_abs = (
        project_root_path / sky_models_base_dir / current_sky_config["filename"]
    ).resolve()
    sky_sec_cfg["file"] = os.path.relpath(
        sky_model_file_abs, current_run_specific_output_dir
    )
    sky_sec_cfg.setdefault("filter", {})["radius_outer_deg"] = sky_module_defaults.get(
        "filter", {}
    ).get("radius_outer_deg")

    return interf_ini_data


def get_sky_model_name_no_ext(sky_model_filename_basename):
    """Helper to get sky model name without extension."""
    return (
        sky_model_filename_basename.rsplit(".", 1)[0]
        if "." in sky_model_filename_basename
        else sky_model_filename_basename
    )


def main(config_file_path):
    """
    Reads the master YAML config, iterates through combinations,
    and generates OSKAR INI files in their respective directories.
    """
    try:
        with open(config_file_path, "r") as f:
            master_config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: Configuration file not found at {config_file_path}")
        return
    except yaml.YAMLError as e:
        print(f"ERROR: Could not parse YAML configuration file: {e}")
        return

    # Extract configurations
    run_settings = master_config.get("run_settings", {})
    output_cfg = master_config.get("output_config", {})
    iter_params = master_config.get("iteration_parameters", {})
    oskar_defaults = master_config.get("oskar_ini_defaults", {})
    executables_cfg = master_config.get("executables", {})

    hyperdrive_cfg = master_config.get("hyperdrive_settings")

    base_output_dir = Path(
        output_cfg.get("base_output_directory", "simulation_outputs_generated")
    )
    images_folder_pattern = output_cfg.get(
        "images_folder_pattern",
        "images_{sky_name_no_ext}_{tel_name}{error_suffix}_{pc_id}",
    )

    beam_ini_filename_template = output_cfg.get("beam_ini_filename", "beam.ini")
    interf_ini_filename_template = output_cfg.get("interf_ini_filename", "interf.ini")
    beam_root_path_base = output_cfg.get("beam_root_path_base", "beam_output")
    interf_ms_base_filename = output_cfg.get("interf_ms_base_filename", "vis.ms")

    # Get iterables
    telescope_configs = iter_params.get("telescope_configs", [])
    sky_model_configs = iter_params.get("sky_model_configs", [])
    sky_models_base_dir_str = iter_params.get("sky_models_base_dir", "sky_models")
    phase_centre_configs = iter_params.get("phase_centre_configs", [])

    if not all([telescope_configs, sky_model_configs, phase_centre_configs]):
        print(
            "Warning: One or more iteration parameter lists (telescopes, skies, phase_centres) are empty. No INI files will be generated."
        )
        return

    run_counter = 0
    for tel_cfg in telescope_configs:
        for sky_cfg in sky_model_configs:
            for pc_cfg in phase_centre_configs:
                run_counter += 1

                tel_name = tel_cfg.get("name", "unknown_tel")
                sky_filename = sky_cfg.get("filename", "unknown_sky.osm")
                pc_id = pc_cfg.get("id", "unknown_pc")

                print(f"\n--- Preparing Config for Run {run_counter} ---")
                print(
                    f"  Telescope: {tel_name}, Sky: {sky_filename}, Phase Centre: {pc_id}"
                )

                # 1. Determine unique output directory for this run
                sky_name_no_ext = get_sky_model_name_no_ext(sky_filename)
                is_errors_globally_on = run_settings.get(
                    "include_telescope_errors", False
                )
                error_suffix = "_errors_on" if is_errors_globally_on else "_errors_off"

                current_run_images_folder_name = images_folder_pattern.format(
                    sky_name_no_ext=sky_name_no_ext,
                    tel_name=tel_name,
                    error_suffix=error_suffix,
                    pc_id=pc_id,
                )
                current_run_output_dir = (
                    base_output_dir / current_run_images_folder_name
                )
                current_run_output_dir.mkdir(parents=True, exist_ok=True)
                print(f"  Output Directory: {current_run_output_dir.resolve()}")

                project_root = Path(".").resolve()

                # --- Generate Beam INI (if enabled) ---
                if run_settings.get("run_beam_sim"):
                    print("  Preparing Beam Simulation INI...")
                    beam_ini_path = current_run_output_dir / beam_ini_filename_template
                    beam_init_data = generate_beam_ini_data(
                        oskar_defaults,
                        tel_cfg,
                        pc_cfg,
                        run_settings,
                        output_cfg,
                        current_run_output_dir,
                        project_root,
                    )

                    write_ini_file_with_configparser(beam_init_data, beam_ini_path)
                    print(f"    Generated beam INI: {beam_ini_path.resolve()}")

                    print(f"    Now running simulation")
                    success = run_oskar_sim_beam(
                        executables_cfg.get(
                            "oskar_sim_beam_patter", "oskar_sim_beam_pattern"
                        ),
                        beam_ini_path,
                        current_run_output_dir,
                        run_settings.get("dry_run", False),
                    )

                    if success and not run_settings.get("dry_run", False):
                        print(f"    Successfully finished OSKAR beam sim")

                # --- Generate Interferometer INI (if enabled) ---
                if run_settings.get("run_interf_sim"):
                    print("  Preparing Interferometer Simulation INI...")

                    interf_ini_data = generate_interf_ini_data(
                        oskar_defaults,  # The 'oskar_ini_defaults' dict from master_config
                        tel_cfg,  # Current telescope config map
                        sky_cfg,  # Current sky model config map
                        pc_cfg,  # Current phase centre config map
                        run_settings,  # The 'run_settings' dict from master_config
                        output_cfg,  # The 'output_config' dict from master_config
                        sky_models_base_dir_str,  # The 'sky_models_base_dir' string from master_config iter_params
                        current_run_output_dir,  # Path object for the run's output dir
                        project_root,  # Path object for project root
                    )

                    interf_ini_path = current_run_output_dir / output_cfg.get(
                        "interf_ini_filename", "interf.ini"
                    )

                    # Assuming write_ini_file_with_configparser is defined
                    write_ini_file_with_configparser(interf_ini_data, interf_ini_path)
                    print(
                        f"    Generated Interferometer INI: {interf_ini_path.resolve()}"
                    )
                    print(f"    Now running simulation")
                    success = run_oskar_sim_interf(
                        executables_cfg.get(
                            "oskar_sim_interferometer", "oskar_sim_interferometer"
                        ),
                        interf_ini_path,
                        current_run_output_dir,
                        run_settings.get("dry_run", False),
                    )

                    if success and not run_settings.get("dry_run", False):
                        print(f"    Successfully finished OSKAR sim")

                if run_settings.get("run_hyperdrive"):
                    run_calibrate(
                        executables_cfg.get("hyperdrive", "hyperdrive"),
                        hyperdrive_cfg,
                        output_cfg,
                        current_run_output_dir,
                        run_settings.get("dry_run", False),
                    )
    print(
        f"\nGenerated configuration for {run_counter} runs in base directory: {base_output_dir.resolve()}"
    )


if __name__ == "__main__":
    # Create a dummy master_simulation_config.yaml for testing if it doesn't exist
    # In a real scenario, this file would be manually created by the user.
    dummy_config_path = "config.yaml"
    if not Path(dummy_config_path).exists():
        print(
            f"Warning: '{dummy_config_path}' not found. Please create it based on the provided template."
        )
        print("You can get the template from the previous assistant message.")

    # --- IMPORTANT: Replace this with the actual path to your YAML configuration file ---
    config_file_to_use = dummy_config_path  # Or your actual file path

    if Path(config_file_to_use).exists():
        main(config_file_to_use)
    else:
        print(f"Please ensure '{config_file_to_use}' exists before running the script.")
