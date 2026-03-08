# BitstreamEvolution
An Open Source Toolchain for the artificial evolution of FPGA bitstreams using genetic algorithms.

# Overview
- Obtain [pico2ice](https://pico2-ice.tinyvision.ai/) development boards
- Set up [iCEFARM](https://github.com/evolvablehardware/iCEFARM/tree/docs?tab=readme-ov-file#icefarm-setup) or obtain access to an existing server
- Set up [BitstreamEvolution](#setup)
- Run [BitstreamEvolution](#usage)

## Temporary iCEFARM Notes
iCEFARM will need to be setup and running before this.
BitstreamEvolution can be run through docker, see [setup](#docker).
```1kz_ice27_generated.asc``` is a clocked 1kHz pulse generator created with verilog and included for use as a seed. This will need to be moved to ```data/seed-hardware``` before running. Alternatively, you can create your own seed. The pulse count firmware listens on pin ICE_27/RPI_GPIO_20. The RANDOM initialization mode should now be working.
The pulse count fitness function is currently overridden regardless of whether you use tolerant or sensitive:
$$\frac{sum(pulses \neq 0)} {MCE(expected, actual)}$$
I've messed around with this one a bit too. It seems to work better for clocked seeds but worse for non clocked seeds:
$$\frac{ \frac {1} {MSE(expected, actual)}} {1 + \sum max(|p-mean(P)| - 0.03*expected, 0)^2}$$
The use of variance promotes circuits to rely on less undefined behavior, which seems to work while when evaluating across multiple devices. This may not be the case after the clock is disabled though.
In addition to the usual python packages, two additional are required:
- icefarm, allows use of icefarm system
- ascutil, provides significantly after circuit mutations

See [```farmconfig.ini```](./farmconfig.ini) for an example config. This is the config used when running through Docker. Configuration values not present in this example config may produce unexpected behavior.
All of the selection methods aside from MAP work. New parameters include annotations.

### Seed file descriptions
- ```1kz_ice27_generated.asc``` is a 1k pulse generator synthesized from verilog with no modifications. No attempt to disable clocks has been made.
- ```ice27_only.asc``` contains routing from pin 27 using io tile 18,31 to logic 18 29. All other tiles are empty and all clocks are in theory unaccessible so long as column restraint notes in ```farmconfig.ini``` is followed.
- ```ice27_only_no_logic.asc``` is the same as previous but with logic tile removed. Requires col 52 (1 index) access to remake connection present in previous. Probably best just to use previous seed but this is included as a minimal working seed.

## Table of Contents
- [BitstreamEvolution](#bitstreamevolution)
  - [Table of Contents](#table-of-contents)
  - [Setup](#setup)
    - [Requirements](#requirements)
    - [Installing the dependencies](#installing-the-dependencies)
    - [Configuring the BistreamEvolution core](#configuring-the-bitstreamevolution-core)
      - [Primary Targets](#primary-targets)
      - [Targets for building Project Icestorm tools](#targets-for-building-project-icestorm-tools)
	  - [Clean targets](#clean-targets)
    - [Docker](#docker)
    - [Issues with setup](#issues-with-setup)
      - [USB permission denied](#usb-permission-denied)
  - [Usage](#usage)
    - [Configuration](#configuration)
      - [Simulation Modes](#simulation-modes)
      - [Fitness Function Parameters](#fitness-function-parameters)
      - [GA parameters](#ga-parameters)
      - [Initialization Parameters](#initialization-parameters)
      - [Stopping Conditions Parameters](#stopping-conditions)
      - [Logging parameters](#logging-parameters)
      - [System parameters](#system-parameters)
      - [Hardware parameters](#hardware-parameters)
    - [Running](#running)
    - [Troubleshooting](#troubleshooting)
  - [Contributing](#contributing)
  - [License](#license)

## Setup
Instructions for setting up the hardware is available at [the Evolvable Hardware website](https://evolvablehardware.org/setup.html).

Setting up BitstreamEvolution involves configuring the
BitstreamEvolution core, the [Project Icestorm](http://www.clifford.at/icestorm/)
tools, and the Arduino components. While BitstreamEvolution should run
on any Linux distribution and likely other Unix-based systems, the
instructions assume you are running a Debian-based distrubtion such as
Debian or Ubuntu. Alternatively, BitstreamEvolution can be run through [Docker](#docker).

### Requirements
BitstreamEvolution requires Python version 3.7 or higher.

BistreamEvolution requires the following libraries and packages:
  * build-essential
  * clang
  * bison
  * flex
  * libreadline-dev
  * gawk
  * tcl-dev
  * libffi-dev
  * libftdi-dev
  * git
  * mercurial
  * graphviz
  * xdot
  * pkg-config
  * python3
  * python3-pip
  * libboost-all-dev
  * cmake
  * make

BitstreamEvolution alse requires the following Python libraries:
  * pyserial
  * matplotlib
  * numpy
  * sortedcontainers
  * icefarm
  * ascutil
  * pytest (optional, used to run tests if desired)

### Installing the dependencies
Each of the dependencies above has a corresponding `apt` package of the
same name. For other package managers the package name may be different.
For Debian-based distributions and other distributions that use `apt`,
the packages can all be installed at once with the following commands:

```bash
sudo apt update && sudo apt upgrade  # Optional, but recommended
sudo apt install build-essential clang bison flex libreadline-dev gawk tcl-dev libffi-dev libftdi-dev mercurial graphviz xdot \
pkg-config python3 python3-pip libboost-all-dev cmake make yosys arachne-pnr
```
The Python libraries can be installed in one command in any Linux
distribution as follows:

```bash
python3 -m pip install pyserial numpy matplotlib sortedcontainers pytest
```
### Configuring the BitstreamEvolution core
Although BitstreamEvolution doesn't require any building or
compilation (other than the Project Icestorm tools), it utilizes make
targets to simplify configuration. The simplest and recommended way to
configure the BitstreamEvolution core is to run `sudo make` in the root
directory of BitstreamEvolution, which will default to running the
target `all`. To allow users to optimize their configuration and save
space (BitstreamEvolution with all its tools is around 2.2 GB), other
targets are exposed. The description of each target is given in the
tables below.

#### Primary targets
These targets are responsible for the setup and configuration of
BitstreamEvolution and some of its dependencies. Note that the `all`
target performs the actions of all other targets (except for the clean
targets). One reason to utilize one of the targets other than `all` is
if the user wants to reconfigure something or if they would like to
manually install or have already installed the Project Icestorm
tools.

|Target|Actions|
|------|-------|
|`all`|Creates the directories for logging data, initializes the default configuration settings installs all the Project Icestorm tools, and creates and writes the udev rules for the PicoIce board|
|`init`|Creates the directories for logging and initializes the default configuration settings|
|`udev-rules`|Creates and writes the udev rules for the PicoIce board|

#### Targets for building Project Icestorm tools
These targets are used to individually build the tools
BitstreamEvolution depends on. In general, they are only useful if some
of the Project Icestorm tools have already been installed and the user
does not want to overwrite the previous installs or wants to save on
disk space.

|Target|Actions|
|------|-------|
|`icestorm-tools`|Builds and installs all the Project Icestorm tools|
|`icestorm`|Builds and install just the icestorm tools (e.g. icepack, iceprog)|
|`arachne-pnr`|Builds and installs just the arachne-pnr tool|
|`yosys`|Builds and installs just the yosys tools|

#### Clean targets
*In general, use of these targets is not recommended*. Since
BitstreamEvolution does not build any intermediate targets, clean
targets are used to get rid of other automatically generated files such
as the workspace defaults and the tools. In particular, cleaning the
latter is not recommended as this makes it more difficult to uninstall
the project Icestorm tools. So far, the primary use of these targets has
been for testing and maintenance of the project.

|Target|Actions|
|------|-------|
|`clean`|Removes the default permanent data logging directories and their contents as well as all the build directories for the Project Icestorm tools (*but it does not uninstall them*)|
|`clean-workspace`|Removes the default permanent data logging directories and their contents|
|`clean-tools`|Removes all the build directories for the Project Icestorm tools (*but it does not uninstall them*)|

### Docker
Note that the live plots will not function while using a container. If it is not yet installed, install [Docker Engine](https://docs.docker.com/engine/install/). You may follow the [post installation steps](https://docs.docker.com/engine/install/linux-postinstall/) so that you do not need to use sudo, but be aware this opens up privilege escalation from your user. Included below:
```
sudo usermod -aG docker $USERNAME
#new shell or log out and then login
newgrp docker
```
Update [farmconfig.ini](farmconfig.ini) to the desired configuration. This is the configuration that will be used. Values not provided will be set to the default. Create the image by running in the project directory:
```
docker build -t bitstreamevolution .
```
Note that after changing configuration values, the image will have to be rebuilt. The same is true for the provided seed file. file.
Next, start the container:
```
docker run -it --network=host bitstreamevolution .venv/bin/python3 src/evolve.py -c farmconfig.ini -d desc
```
You may replace desc with an accurate experiment description. Note that changing the farmconfig.ini parameter will only work if that file has been included in the docker image. The ```-it``` flag streams output to the terminal, but closing it will end the experiment. This flag can be omitted if desired. If you choose to omit this flag, you can obtain the container logs by first getting the name of the container with ```docker container ls``` and then running ```docker logs <container name>```.

#### Viewing live plots from a container

Since the container has no display server, matplotlib cannot open windows directly. There are two ways to view plots while an experiment is running: a **live volume mount** (recommended) or a **manual snapshot copy**.

##### Live volume mount (recommended)

This approach mounts the container's `workspace/` directory to your host so that log files appear in real time, allowing `PlotEvolutionLive.py` to update continuously on your machine.

**1. Install the plotting dependencies on your host.** Only `matplotlib` and `numpy` are required (the other project dependencies are not needed):
```bash
pip install matplotlib numpy
```

**2. Start the container with a volume mount from the project directory.** Add `-v ./workspace:/usr/local/app/workspace` to your `docker run` command. The left side (`./workspace`) is a path on your host relative to where you run the command, and the right side (`/usr/local/app/workspace`) is the path inside the container. The `--user` flag ensures files are created with your host user's ownership (without it, Docker runs as root and the plotting script will get permission errors writing to `workspace/plots/`). Run this from the project root so that the log files appear in your local `workspace/` folder:
```bash
docker run -it --network=host --user $(id -u):$(id -g) \
  -v ./workspace:/usr/local/app/workspace \
  -v ./farmconfig.ini:/usr/local/app/farmconfig.ini \
  bitstreamevolution .venv/bin/python3 src/evolve.py -c farmconfig.ini -d desc
```
The first `-v` flag mounts the workspace so log files appear on your host in real time. The second `-v` flag mounts your local `farmconfig.ini` into the container, so configuration changes take effect immediately without rebuilding the Docker image. As the experiment runs, the `workspace/*.log` files will appear and update on your host filesystem.

**3. In a separate terminal, start the plotting script on your host:**
```bash
python3 src/PlotEvolutionLive.py
```
The plots will read from `workspace/` and auto-refresh every few seconds as new generations complete. You can leave this running for the duration of the experiment.

##### Manual snapshot copy (fallback)

If you cannot install Python dependencies on the host, you can copy the workspace out of a running container for a one-time snapshot. First, find the container name:
```bash
docker container ls
```
Then copy the workspace directory. **This will overwrite any existing local `workspace/` folder:**
```bash
docker cp <container name>:/usr/local/app/workspace workspace
```
Start the plotting script to view the snapshot:
```bash
python3 src/PlotEvolutionLive.py
```
Re-run the `docker cp` command whenever you want an updated snapshot.

### Issues with setup:
This section describes some issues that can be encountered during
installation and how to address them. If the following steps do not
address your issue or you encounter other problems, please file an issue
[here](https://github.com/evolvablehardware/BitstreamEvolution/issues) so that
we can look into it.

## Usage
This section describes how to run the configure and run
BitstreamEvolution. For the most part, BitstreamEvolution can be run
as-is without configuration; the only part of the configuration file
that needs to be modified is the
[Arduino device file path](#system-parameters).

<!--
  TODO Configuration options that need to be changed should be
  better highlighted and emphasized. Ideally, the program would ensure
  that the user has set these before running (and they would be unset by
  default
-->
### Configuration
The project has various configuration options that can be specified in
`data/config.ini`. The file`data/default_config.ini` contains the
default options for the configuration and should not be modified.

The `TOP-LEVEL PARAMETER` `base_config` can be modified to specify a base config file.
In the event of a missing config parameter, it will be filled in with that from the base config file.
These can be stacked into a line of configuration files.
The configuration files will be combined and the resulting file to use for evolution will
be output. All parameters still must be specified at some point in the final configuration.

Below is a list of the options, their description, and their possible values:

<!-- NOTE Right now this only lists the most important options-->

#### Simulation Modes
| Mode | Description |
|--------|-------------|
| FULLY_INTRINSIC | Compiles hardware files, then uploads to FPGA |
| REMOTE | Same as FULLY_INTRINSIC, but evaluates circuits remotely using iCEFARM system after compilation |
| SIM_HARDWARE | Compiles hardware files, but arbitrarily evaluates fitness all on the host computer. This option is useful for verifying that mutation and crossover are functional |
| FULLY_SIM | Generates a bitstream that represents a sum of sine waves. This is treated as a waveform generated by a variance measure |


*Note: FULLY_INTRINSIC or REMOTE should be used unless verification of some process is being done

#### Fitness Function Parameters
| Parameter | Description | Possible Values | Recommended Values |
|-----------|-------------|-----------------|--------------------|
| Fitness function | The fitness function to use | TOLERANT_PULSE_COUNT, SENSITIVE_PULSE_COUNT, VARIANCE, COMBINED |  |
| Desired frequency | If using the pulse fitness function, the target frequency of the evolved oscillator | (In Hertz) 1 - 1000000 | 1000 |
| COMBINED_MODE | If using the combined fitness function, how to combine the fitnesses | ADD, MULT | |
| PULSE_WEIGHT | If using the combined fitness function, what weigthing to use for closeness to the trigger voltage in combined fitness| 0.0 - 1.0 | |
| VAR_WEIGHT | If using the combined fitness function, what weigthing to use for variance in combined fitness | 0.0 - 1.0 | |
| NUM_SAMPLES | Number of samples to record in pulse count fitness functions. The minimum number recorded will be used to determine the actual pulse fitness. Higher number of samples will take longer to
run, but should result in more stable circuits | 1+ | 1-5 |

#### GA parameters
| Parameter | Description | Possible Values | Recommended Values |
|-----------|-------------|-----------------|--------------------|
| Population size | The number of circuits to evolve | 2 - 1000+ | 10 - 50 |
| Mutation type | Mutation algorithm to use | Simple, Rank, Proportional, Convergence | Rank |
| Mutation probability | The probability to flip a bit of the bitstream during mutation | 0.0 - 1.0 | (1 / genotypic length) = 0.0021 |
| Crossover probability | The probability of replacing a bit in one bitstream from a bit from another during crossover | 0.0 - 1.0 | 0.1 - 0.5 |
| Elitism fraction | The percentage of most fit circuits to protect from modification in a given generation | 0.0 - 1.0 | 0.1 |
| Selection | The type of selection to perform | SINGLE_ELITE, FRAC_ELITE, CLASSIC_TOURN, FIT_PROP_SEL, RANK_PROP_SEL | FIT_PROP_SEL |
| Diversity measure | The method to use to measure diversity | NONE, UNIQUE, HAMMING_DIST | HAMMING_DIST |
| Random injection | Thr probability of randomly injecting circuits into each generation | 0.0 - 1.0 | 0.0 - 0.15 |
| Chaos injection | Randomly performs additional mutations on 10% of circuits after 5 generations without fitness increase. Mutations are done at mutation_chance * chaos_injection | 0.0+ | 5 |

##### Selection methods
| Method | Description |
|--------|-------------|
| SINGLE_ELITE | Mutates the hardware of every circuit that is not the current best circuit |
| FRAC_ELITE | Creates a group of elite circuits from the population whose size is based on the elitism percentage. Mutates the hardware of and performs crossover on every non-elite |
| CLASSIC_TOURN | Randomly pairs together every circuit in the population and compares them. Keeps the winner the same and mutates and performs crossover on the loser |
| FIT_PROP_SEL | Creates a group of elite circuits from the population whose size is based on the elitism percentage. Every non-elite is compared to a random elite chosen based on the elites' fitnesses and is mutated and crossed with the elite |
| RANK_PROP_SEL | Same as above, but the elite is chosen randomly based on the elites' ranks |
| MAP_ELITES | MAP Elites-inspired selection method, for variance experiments. Maps circuits based on min/max voltage into 50x50 cells. The top individuals in each cell are copied and mutated for the next generation. |

#### Initialization Parameters
| Parameter | Description | Possible Values | Recommended Values |
|-----------|-------------|-----------------|--------------------|
| Init mode | The method to generate the initial random circuits | CLONE_SEED, CLONE_SEED_MUTATE, RANDOM, EXISTING_POPULATION | RANDOM, CLONE_SEED_MUTATE |
| Randomize until | The method used for randomizing the initial population | PULSE, VARIANCE, NO | NO |
| Randomize threshold | The target fitness for initial random search before evolution begins| 3-8 | 4 |
| Randomize mode | The method to use when "randomizing" each circuit | MUTATE, RANDOM | Depends on the situation. If a seed individual/population is used, then use MUTATE. Otherwise, use RANDOM |
| Seed | Circuit path to use as seed | Any .asc filepath | data/seed-hardware.asc |

##### Initialization Modes
| Mode | Description |
|--------|-------------|
| CLONE_SEED | Clones the seed hardware to every individual in the population (i.e. all individuals are the same at the start) |
| CLONE_SEED_MUTATE | Clones the seed hardware to every individual in the population, and mutates each individual |
| RANDOM | Randomly assigns all (modifiable) bits of each individual |
| EXISTING_POPULATION | Completely copies the existing population from the specified directory |

*Note: The FULLY_SIM simulation mode will use the RANDOM initialization mode every time

#### Stopping Conditions
| Parameter | Description | Possible Values | Recommended Values |
|-----------|-------------|-----------------|--------------------|
| Generations | The maximum number of generations to iterate through | 2 - 1000+ or IGNORE | 50 - 500 |
| Target Fitness | The goal fitness; evolution terminates once any individual reaches this | 1-1000+ or IGNORE | IGNORE |

#### Logging parameters
| Parameter | Description | Possible Values | Recommended Values |
|-----------|-------------|-----------------|--------------------|
| Log Level | The amount of logs to show; higher log level means more detailed logs are shown | 1-4 | 2 |
| Save Log | Wether or not to save the logging output in a file | true, false | true |
| Save Plots | Wether or not to save the plots as images throughout evolution | true, false | true |
| Log Scale Pulses | Use symmetric log scale for pulse count y-axes | true, false | false |
| Log Scale Fitness | Use symmetric log scale for the fitness y-axis, with a reference line at fitness=1.0 | true, false | false |
| Backup Workspace | Wether or not to save the workspace directory in a backup folder after evolution | true, false | true |
| Log File | The file to save log output in | Any file path | ./workspace/log |
| Plots Directory | The directory to put the plots in | Any directory | ./workspace/plots |
| Output Directory | The directory to store previous workspaces in | Any directory not in ./workspace | ./prev_workspaces |
| ASC Directory | The directory to put the asc files (raw bitstreams) | Any directory | ./workspace/experiment_asc |
| BIN Directory | The directory to put the bin files (compiled bitstreams) | Any directory | ./workspace/experiment_bin |
| Data Directory | The directory to put the data files (MCU read data) | Any directory | ./workspace/experiment_data |
| Analysis Directory | The directory to put the analysis files | Any directory | ./workspace/analysis || Best file | The path to put the asc file of the best performing circuit throughout evolution | Any file path | ./workspace/best.asc |
| Source Populations Directory | The directory consisting of source populations to use in initialization | Any directory | ./workspace/source_populations |
| Generations Directory | The directory to put generation files into, when populations are saved each generation. The reconstruct command pulls from this directory | Any directory | ./workspace/generations |
| Use Overall Best | Whether or not to draw the overall best line in the plots | true or false | true |

#### System parameters
| Parameter | Description | Possible Values |
|-----------|-------------|-----------------|
| USB Path | The path to the USB device file | Any device file path (e.g. `/dev/ttyUSB0`) |

#### Hardware parameters
| Parameter | Description | Possible Values | Recommended Values |
|-----------|-------------|-----------------|--------------------|
| Routing | Specifies what surround tiles a logic tile can connect to | MOORE, NEWSE | MOORE |
| MCU Read Timeout | How long to wait to read from the mcu | 1+ | 1.1|
| Serial Buad | The baudrate to use for serial communication | 300, 600, 1200, 2400, 4800, 9600, 14400, 19200, 28800, 31250, 38400, 57600, and 115200 | 115200 |
| Accessed Columns | The columns in each logic tile's bitstream to modify throughout evolution | List of comma seperated numbers from 0 to 53 | 14,15,24,25,40,41|

#### iCEFARM parameters
| Parameter | Description | Possible Values |
|-----------|-------------|-----------------|
| Url | Url to iCEFARM control server | Any Url |
| Mode | How to distribute evaluations across remote devices | quick, all |
| Devices | Amount of devices to reserve from iCEFARM | 1+ |

### Running
From the root directory of BitstreamEvolution run:

```bash
python3 src/evolve.py
```

| Options | Description |
|-----------|-------------|
| -c | The config file this experiment uses |
| -d | The experiment description |
| -o | The output directory to store in the workspace in |

BitstreamEvolution will begin to run and display information in separate windows
that will appear (unless these have been disabled in the configuration).

BitstreamEvolution will continue to run until one of the following happens:
  * It has run through the specified number of generations
  * It has met the specified conditions
  * It is terminated in some other form (e.g. ctrl-c, shutdown, etc.)

### Running Test Cases
Test case files are simple to run using the pytest framework.
To run the entire suite:
```bash
pytest "test/"
```
You can also specify the desired file to run:
```bash
pytest "test/test_config_builder.py"
```
Alternatively, you can run individual tests within a file like so:'
```bash
pytest "test/file.py::function"
```

## Tools
### Generation Reconstruction
The code will automatically save each generation to a generation file in the generations directory (which is specified in the config)

You can later reconstruct generations. This will bring the generation back into your ASC directory. This is done by running `python3 src/tools/reconstruct.py [generation #]`

### Pulse Count Histogram
You can view a histogram of pulse counts for an entire experiment or particular generations using the pulse count histogram tool. Simply run `python3 src/tools/pulse_histogram.py`, and it will show the results for the last-run experiment (pulling from `workspace/pulselivedata.log`). A negative pulse count indicates the the microcontroller timed out five times in a row, and so no reading was recorded.

## Contributing
<!--TODO ALIFE2021 define the desired approach -->
Join the movement! Email derek.whitley1@gmail.com to get added to the Slack group.

## License
This project is licensed under the GNU GPL v3 or later. For more
information see [LICENSE](LICENSE).
