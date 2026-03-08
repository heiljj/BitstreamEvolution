"""
Circuit Population
------------------

This class was reviewed, and should be fully documented at a basic level.

"""
import os
import numpy as np
from shutil import copyfile
from sortedcontainers import SortedKeyList
from numpy.random import default_rng
from pathlib import Path
from collections import namedtuple
from time import time
import atexit
import random
import math
from mmap import mmap
from Circuit.FileBasedCircuit import FileBasedCircuit
from Circuit.FullySimCircuit import FullySimCircuit
from Circuit.IntrinsicCircuit import IntrinsicCircuit
from Circuit.PulseCountFitnessFunction import PulseCountFitnessFunction
from Circuit.SimHardwareCircuit import SimHardwareCircuit
from Circuit.CGPIntrinsicCircuit import CGPIntrinsicCircuit
from Circuit.ToneDiscriminatorFitnessFunction import ToneDiscriminatorFitnessFunction
from Circuit.VarMaxFitnessFunction import VarMaxFitnessFunction
from Circuit.RemoteCircuit import RemoteCircuit, EvolutionClient
from ga.selection.utils import selection_fac
from ga.diversity import diversity_fac
from Config import Config
from ascTemplateBuilder import ascTemplateBuilder
from utilities import wipe_folder
from datetime import datetime
import random

from icefarm.client.drivers import PulseCountClient, VarMaxClient

RANDOMIZE_UNTIL_NOT_SET_ERR_MSG = '''\
RANDOMIZE_UNTIL not set in config.ini, continuing without randomization'''

INVALID_VARIANCE_ERR_MSG = '''\
VARIANCE_THRESHOLD <= 0 as set in config.ini, continuing without randomization'''

# SEED_HARDWARE is the hardware file used as an initial template for the Circuits
# NOTE The Seed file is provided as a way to kickstart the evolutionary process
# without having to perform a time-consuming random search for a seedable circuit.
# Contact repository authors if you're interested in a new seed file.

# The basename (filename without path or extensions) of the Circuit
# hardware, bitstream, and data files.
CIRCUIT_FILE_BASENAME = "hardware"


# Create a named tuple for easy and clear storage of information about
# a Circuit (currently its name and fitness)
CircuitInfo = namedtuple("CircuitInfo", ["name", "fitness"])

# Named tuple for circuit's path and fitness; currently only used for combining populations
CircuitPathInfo = namedtuple("CircuitPathInfo", ["path", "fitness"])


def is_pulse_func(config):
    """
    Used in multiple places, will be removed soon.

    .. todo::
        unite the is_pulse_func() functions for ease of change.

    Parameters
    ----------
    config : Config
        Configuration Class to interact with config

    Returns
    -------
    bool
        True if it is any type of oscilator (uses count pulses), False otherwise.
    """
    return (config.get_fitness_func() == 'PULSE_COUNT' or config.get_fitness_func() == 'TOLERANT_PULSE_COUNT'
            or config.get_fitness_func() == 'SENSITIVE_PULSE_COUNT' or config.get_fitness_func() == 'PULSE_CONSISTENCY')

class CircuitPopulation:
    """Manages the initializing the population of circuits,
    updating and recording information about the population throughout evolution,
    and deciding when to stop evolution"""
    # SECTION Initialization functions
    def __init__(self, mcu, config: Config, logger, clear_workers=False, speedtest=False):
        """
        Generates the initial population of circuits with the following arguments

        Parameters
        ----------
        mcu : Microcontroller
            Object containing an instance of Microcontroller class
        config : Config
            Object containing an instance of Config class
        logger : Logger
            Object containing an instance of Logger class
        clear_workers : bool
            If True, clear stale worker records from iCEFARM before reserving
        speedtest : bool
            If True, record per-generation timing data to workspace/speedtest.csv
        """
        self.__config = config
        self.__microcontroller = mcu
        self.__speedtest = speedtest

        if config.get_simulation_mode() == "REMOTE":
            url = config.get_icefarm_url()
            # TODO generate unique client name / stop procrastinating on auth
            name = f"bitstream-evolution-{random.random()}"
            if config.get_fitness_func() == "VARIANCE":
                if config.get_icefarm_send_waveform():
                    logger.info("Waveform data transfer enabled")
                self._client = VarMaxClient(url, name, logger, send_waveform=config.get_icefarm_send_waveform())
            else:
                self._client = PulseCountClient(url, name, logger)
            if clear_workers:
                logger.info("Clearing stale workers...")
                self._client.clearWorkers()
                logger.info("Cleared. Waiting for workers to re-register...")
            logger.info(f"Reserving devices...")
            self._client.reserve(int(config.get_icefarm_devices()), wait_for_available=clear_workers, flush_interval_seconds=config.get_icefarm_results_flush_interval_seconds(), flush_at_bitstreams_remaining=config.get_icefarm_buffer_batch_amount() * config.get_icefarm_client_batch_amount_circuits() - 1)
            logger.info(f"Reserved devices: {self._client.getSerials()}")
            self._evo_client = EvolutionClient(self._client, logger, config.get_icefarm_client_batch_amount_circuits(), config.get_icefarm_buffer_batch_amount())
            atexit.register(self._client.endAll)
        else:
            self._client = None


        # A list of Circuits that's sorted by fitness decreasing order
        # (to get it to sort in decreasing order I had to multiply the
        # sort key by negative one to reverse the natural sorting order
        # since sortedcontainers don't have a way to be in reverse order).
        self._circuits = SortedKeyList(key=lambda ckt: -1 * ckt.get_fitness())
        self.__logger = logger
        self.__overall_best_circuit_info = CircuitInfo("", 0)
        self.__rand = default_rng()
        self.__current_epoch = 0
        self.__best_epoch = 0

        num_rows = len(config.get_routing_rows())
        num_cols = len(config.get_accessed_columns())
        # 660 logic tiles - no tiles for x=6 or x=19
        self.__population_bistream_sum = np.zeros(660*num_rows*num_cols)

        self.__run_selection = selection_fac(self, config, logger, self.__rand)
        self.__run_diversity = diversity_fac(config, logger)

    def run_fitness_sensitity(self):
        """
        Gets the same circuit, runs it repeatedly and reports each fitness.
        Internally has a while loop to determine how many times to run.
        """
        #create circuit object
        self.__logger.info("Creating circuit object for fitness sensitivity experiment")
        ckt = self.__construct_circuit(
            1,
            "hardware1",
            self.__config.get_test_circuit(),
            self.__generate_sine_funcs()
        )

        using_time = self.__config.using_sensitivity_time()
        start_time = time()
        stop_time = self.__config.get_sensitivity_time()

        using_trials = self.__config.using_sensitivity_trials()
        cur_trial = 0
        num_trials = self.__config.get_sensitivity_trials()

        #loop through trials and log fitness
        should_continue = True
        while should_continue:
            self.__eval_circuit_once(ckt)
            fitness = ckt.get_fitness()

            with open("workspace/fitnesssensitivity.log", "a") as live_file:
                if self.__config.is_pulse_func():
                    data2 = ckt.get_extra_data('pulses')
                else:
                    data2 = ckt.get_extra_data('mean_voltage')

                #get temp and humidity reading
                t = 0
                h = 0
                if(self.__config.reading_temp_humidity()):
                    pass
                    # TODO
                    # t = self.__microcontroller.measure_temp()
                    # h = self.__microcontroller.measure_humidity()
                    # self.__logger.event(4, "Recorded temperature: " + str(t) + ". Recorded humidity: " + str(h))


                now = datetime.now()
                timestamp = now.strftime("%H.%M.%S")

                live_file.write(("{}:{},{},{},{},{}\n").format(str(cur_trial), fitness, data2, t, h, timestamp))
            self.__logger.event(2, "Trial " + str(cur_trial) + " done. Fitness recorded and logged to file: " + str(fitness))

            cur_trial += 1
            should_continue = ((not using_time) or (time() - start_time < stop_time)) and \
                              ((not using_trials) or (cur_trial < num_trials))

        self.__logger.event(1, "Fitness sensitivity trails done.")

    def __generate_sine_funcs(self):
        """
        Builds a list of randomly generated sine functions used in the simulation mode.

        Returns
        -------
        list[functions]
            List of randomly generated sine functions
        """
        sine_funcs = []
        self.__sine_strs = []
        for i in range(100):
            # Don't let amplitude and y-offset get too out of hand
            a = random.uniform(0, 100)
            b = random.uniform(0.02, 2)
            c = (random.randint(0, 7) / 8) * (2 * math.pi / b)
            d = random.uniform(100, 900)
            # We provide many parameters with default values here, because Python closures
            # work like JS using the "var" keyword, and do not "properly" create environments the way we'd expect
            # For this reason, we add default parameters, providing our current var values to them
            # This works because the variable values are then *evaluated* as the lambda (closure) is constructed
            # Before this fix, we had a bug where every single sine function would be exactly the same;
            # all holding a/b/c/d values from the very last function to be generated
            sine_funcs.append((lambda x,a=a,b=b,c=c,d=d: a * math.sin(b * (x + c)) + d))
            sine_str = "Sine function: " + str(i) + " | y = " + str(a) + " * sin(" + str(b) + " * (x + " + str(c) + ")) + " + str(d)
            self.__sine_strs.append(sine_str)
        return sine_funcs

    def __construct_circuit(self, index, file_name, seed_arg, sine_funcs):
        if self.__config.get_simulation_mode() == 'FULLY_SIM':
            return FullySimCircuit(index, file_name, self.__config, sine_funcs, self.__rand)
        elif self.__config.get_simulation_mode() == 'SIM_HARDWARE':
            return SimHardwareCircuit(index, file_name, self.__config, seed_arg, self.__logger, self.__rand)
        elif self.__config.get_simulation_mode() == "FULLY_INTRINSIC_CGP":
                return CGPIntrinsicCircuit(index, file_name, self.__config, seed_arg, self.__rand, self.__logger, self.__microcontroller, PulseCountFitnessFunction())
        else:
            fit_func = None
            if self.__config.get_fitness_func() == 'VARIANCE':
                fit_func = VarMaxFitnessFunction(500)
            elif self.__config.get_fitness_func() in ['PULSE_COUNT', 'SENSITIVE_PULSE_COUNT', 'TOLERANT_PULSE_COUNT']:
                fit_func = PulseCountFitnessFunction()
            elif self.__config.get_fitness_func() == 'TONE_DISCRIMINATOR':
                fit_func = ToneDiscriminatorFitnessFunction()

            if self.__config.get_simulation_mode() == 'REMOTE':
                if self.__config.get_icefarm_mode().upper() == "ALL":
                    serials = self._client.getSerials()
                else:
                    serials = None

                return RemoteCircuit(self._evo_client, serials, index, file_name, self.__config, seed_arg, self.__rand, self.__logger, fit_func)

            return IntrinsicCircuit(index, file_name, self.__config, seed_arg, self.__rand, self.__logger, self.__microcontroller, fit_func)

    def populate(self):
        """
        Creates initial population based on the config.
        1. Clears the files used to keep track of circuit
        2. Uses appropriate initialization method specified by config.
        3. Handles randomization until condition in config is met.
        """
        # Always creates a circuit with the seed file, but if we have certain randomization
        # modes then perform necessary operations
        sine_funcs = self.__generate_sine_funcs()

        # Wipe the current folder, so if we go from 100 circuits in one experiment to 50 in the next,
        # we don't still have 100 (with 50 that we use and 50 residual ones)
        wipe_folder(self.__config.get_asc_directory())
        wipe_folder(self.__config.get_bin_directory())
        wipe_folder(self.__config.get_data_directory())
        wipe_folder(self.__config.get_generations_directory())

        self.__multiple_populations = False
        if self.__config.get_init_mode() == "EXISTING_POPULATION":
            # Need to assign where each circuit gets its source from
            # Get number of subpopulations, then grab random circuits from each
            subdirectories = next(os.walk(self.__config.get_src_pops_dir()))[1]
            subdirectory_files = list(map(lambda dir: next(os.walk(self.__config.get_src_pops_dir().joinpath(dir)))[2], subdirectories))
            self.__num_subpops = len(subdirectories)
            self.__multiple_populations = True
            # Existing population setting, load in all circuits from each population and get the ones with the highest fitness
            # If any are missing the fitness measure, then we will randomly select them.
            # We could manually measure their fitnesses, but as of now we've decided that is too slow
            all_subdir_circuits = []
            for i in range(len(subdirectories)):
                # Load every circuit
                subdir_circuits = SortedKeyList(
                    key=lambda ckt: -ckt.fitness
                )
                for file in subdirectory_files[i]:
                    path = self.__config.get_src_pops_dir().joinpath(subdirectories[i]).joinpath(file)
                    hw_file = open(path, "r+")
                    mmapped_file = mmap(hw_file.fileno(), 0)
                    hw_file.close()
                    fitness = float(FileBasedCircuit.get_file_attribute_st(mmapped_file, "fitness"))
                    if fitness == None:
                        fitness = 0
                    subdir_circuits.add(CircuitPathInfo(path, fitness))

                all_subdir_circuits.append(subdir_circuits)
        subdirectory_index = 0

        # if we're using custom i/o pin configurations
        # need to configure to io tiles of the seed circuit
        template = self.__config.get_seed_fpath()
        if self.__config.get_using_configurable_io():
            template = "workspace/template/seed.asc"
            template_builder = ascTemplateBuilder(self.__config, self.__logger)
            template_builder.configure_seed_io(self.__config.get_seed_fpath(), template)

        for index in range(1, self.__config.get_population_size() + 1):
            file_name = "hardware" + str(index)
            if self.__config.get_init_mode() == "EXISTING_POPULATION":
                # Grab the top circuit from the current population, unless it is empty, then we'll jump to the next one
                while len(all_subdir_circuits[subdirectory_index]) <= 0:
                    subdirectory_index = (subdirectory_index + 1) % len(all_subdir_circuits)
                seedArg = all_subdir_circuits[subdirectory_index].pop(0).path
                subdirectory_index = (subdirectory_index + 1) % len(all_subdir_circuits)
            else:
                seedArg = template


            ckt = self.__construct_circuit(index, file_name, seedArg, sine_funcs)
            if self.__config.get_init_mode() == "RANDOM":
                ckt.randomize_bitstream()
            elif self.__config.get_init_mode() == "CLONE_SEED_MUTATE":
                # Call mutate once on this circuit
                ckt.mutate()
                print("populate")
            elif self.__config.get_init_mode() == "EXISTING_POPULATION":
                # Make sure the circuit puts a line at the top of its .asc file denoting the source population
                ckt.set_file_attribute('src_population', str(subdirectory_index))

            self._circuits.add(ckt)
            self.__logger.event(3, "Created circuit: {0}".format(ckt))

        # If map-elites selection method selected, then randomly generate until we fill up 25% of the map

        # if self.__config.get_selection_type() == 'MAP_ELITES':
        #     self.__logger.event(1, 'Randomizing until map is 25% full...')
        #     elites = list(filter(lambda x: x != 0, [j for sub in self.__generate_map() for j in sub]))
        #     elite_count = len(elites)
        #     while elite_count < 0.1 * (21 * 21 / 2):
        #         self.__logger.event(3, "Got %s%% (%s)" % (elite_count / (21*21/2) * 100, elite_count))
        #         # Need to mutate non-elites
        #         for ckt in self.__circuits:
        #             if not ckt in elites:
        #                 ckt.copy_sim(random.choice(elites))
        #                 ckt.mutate()
        #                 #ckt.randomize_bitstream()
        #                 ckt.evaluate_sim(False)

        #         elite_map = self.__generate_map()
        #         elites = list(filter(lambda x: x != 0, [j for sub in elite_map for j in sub]))
        #         elite_count = len(elites)
        #         self.__output_map_file(elite_map)

        # Randomize initial circuits until waveform variance or
        # pulses are found
        if self.__config.get_simulation_mode() not in ["FULLY_INTRINSIC", "REMOTE"]:
            pass # No randomization implemented for simulation mode
        elif self.__config.get_randomization_type() == "PULSE":
            self.__logger.info("PULSE randomization mode selected.")
            self.__randomize_until_pulses()
        elif self.__config.get_randomization_type() == "VARIANCE":
            self.__logger.info("VARIANCE randomization mode selected.")
            if self.__config.get_randomize_threshold() <= 0:
                self.__logger.error(INVALID_VARIANCE_ERR_MSG)
            else:
                self.__randomize_until_variance()
        elif self.__config.get_randomization_type() == "VOLTAGE":
            self.__randomize_until_voltage()
        elif self.__config.get_randomization_type() == "NO":
            self.__logger.info("NO randomization mode selected.")
        else:
            self.__logger.error(RANDOMIZE_UNTIL_NOT_SET_ERR_MSG)

        # Output the first data point to live data files
        self.__write_to_livedata()

    def __randomize_until_pulses(self):
        """
        Randomizes population until minimum number of pulses is found.
        Called by populate(self)
        Should only be used with pulse count fitness functions
        """
        no_pulses_generated = True
        while no_pulses_generated:
            # NOTE Randomize until pulses will continue mutating and
            # not revert to the original seed-hardware until restarting
            self.__logger.event(3, "Randomizing to generate pulses")
            for circuit in self._circuits:
                if self.__config.get_randomize_mode() == 'RANDOM':
                    circuit.randomize_bitstream()
                else:
                    circuit.mutate()

            for circuit in self._circuits:
                circuit.evaluate_once()

            # used by remotecircuit to fetch data
            if self.__config.get_simulation_mode() == 'REMOTE':
                for circuit in self._circuits:
                    circuit.calculate_fitness()

            for circuit in self._circuits:
                pulses = circuit.get_extra_data('pulses')
                if self.__config.get_simulation_mode() == 'REMOTE':
                    pulses = min(pulses)
                th = self.__config.get_randomize_threshold()
                if (pulses > th):
                    no_pulses_generated = False
                    self.__logger.info(f"Pulse generated! Exiting randomization. Pulses recorded: {pulses} circuit: {circuit}")
                    break

    def __randomize_until_voltage(self):
        """
        Randomizes population until a mean voltage is found near the desired value
        called by populate(self)
        Should only be used with variance maximization fitness function
        """
        while True:
            self.__logger.event(3, "Randomizing to get voltage")
            for circuit in self._circuits:
                if self.__config.get_randomize_mode() == 'RANDOM':
                    circuit.randomize_bitstream()
                else:
                    circuit.mutate()

                circuit.evaluate_once()
                mean_voltage = circuit.get_extra_data('mean_voltage')
                if (abs(mean_voltage - 341) < 10):
                    self.__logger.info("Voltage Achieved! Exiting randomization. Voltage:", mean_voltage)
                    break

    # NOTE This is whole function going to be upgraded to handle a from-scratch circuit seeding process.
    # https://github.com/evolvablehardware/BitstreamEvolution/issues/3
    def __randomize_until_variance(self):
        """
        Randomizes population until minimum variance fitness is found.
        called by populate(self)
        Should only be used with variance maximization fitness function
        """
        bestVariance = 0
        variance = 0
        while bestVariance < self.__config.get_randomize_threshold():
            self.__logger.event(3, "Randomizing to generate variance")

            # Phase 1: Randomize and compile all circuits
            for circuit in self._circuits:
                circuit.clear_data()
                circuit.randomize_bitstream()

            # Phase 2: Queue all evaluations (batched across devices)
            for circuit in self._circuits:
                circuit.evaluate_once()

            # Phase 3: Calculate fitness (first call triggers batch send to all devices)
            for circuit in self._circuits:
                circuit.calculate_fitness()

            # Phase 4: Check results
            for circuit in self._circuits:
                variance = circuit.get_fitness()
                self.__logger.info(f"Variance generated: {variance}")

                with open("workspace/randomizationdata.log", "a") as liveFile:
                    liveFile.write(str(variance) + "\n")

                if variance > bestVariance:
                    self.__logger.info(f"New best variance: {variance}")
                    bestVariance = variance
                    self.__overall_best_circuit_info = CircuitInfo(str(circuit), variance)
                    copyfile(circuit.get_hardware_file_path(), self.__config.get_best_file())

        self.__logger.info(f"Variance generated! Exiting randomization. Fitness: {bestVariance}")

    def __next_epoch(self):
        """
        Moves to the next generation/epoch
        Currently, only needs to increase the generation by 1
        All other generation-specific behavior will be derived from this value
        """
        self.__current_epoch += 1

    def __should_continue_evo(self):
        """
        Checks with config whether we have reached any of the end conditions for the simulation run.

        Returns
        -------
        bool
            True if evolution should continue, False otherwise.
        """
        should_continue = True
        if self.__config.using_n_generations():
            if self.get_current_epoch() >= self.__config.get_n_generations():
                should_continue = False
        if self.__config.using_target_fitness():
            if self.__overall_best_circuit_info.fitness >= self.__config.get_target_fitness():
                should_continue = False
        return should_continue

    def __eval_circuit_once(self, circuit):
        circuit.clear_data()
        if isinstance(circuit, FileBasedCircuit):
            circuit.upload()
        for i in range(self.__config.get_num_samples()):
            circuit.collect_data_once()

        circuit.calculate_fitness()

    def evolve(self):
        """
        Runs an evolutionary loop and records the circuit with the highest fitness throughout the loop,
        while also storing statistics in a file for the plot to access.
        """
        if len(self._circuits) == 0:
            self.__logger.error(
                1, "Attempting to evolve with empty population. Exiting...")
            exit()

        # Set initial values for 'best' data
        self.__overall_best_circuit_info = CircuitInfo(
            str(self._circuits[0]),
            self._circuits[0].get_fitness()
        )
        self.__best_epoch = 0
        self.__next_epoch()

        if self.__speedtest:
            send_wf = self.__config.get_icefarm_send_waveform() if self.__config.get_simulation_mode() == "REMOTE" else False
            with open("workspace/speedtest.csv", "w") as f:
                f.write(f"# send_waveform={send_wf}, population={self.__config.get_population_size()}, devices={self.__config.get_icefarm_devices() if self.__config.get_simulation_mode() == 'REMOTE' else 'local'}\n")
                f.write("generation,epoch_time_s,best_fitness,avg_fitness\n")

        while(self.__should_continue_evo()): #self.get_current_epoch() < self.__config.get_n_generations()):

            #self.__logger.event(3, "Starting evo cycle", self.get_current_epoch(
            #), "<", self.__config.get_n_generations(), "?")

            # Since sortedcontainers don't update when the value by
            # which an item is sorted gets updated, we have to add the
            # Circuits to a new list after we evaluate them and then
            # make the new list the working Circuit list.
            reevaulated_circuits = SortedKeyList(
                key=lambda ckt: -ckt.get_fitness()
            )

            # Evaluate all the Circuits in this CircuitPopulation.
            start = time()

            for circuit in self._circuits:
                circuit.clear_data()

            for _ in range(self.__config.get_num_passes()):
                for circuit in self._circuits:
                    if isinstance(circuit, FileBasedCircuit):
                        circuit.upload()

                    # TODO imo we can remove this now that we're using picos since the
                    # upload happens essentially instantly compared to the evaluation time
                    for i in range(self.__config.get_num_samples()):
                        circuit.collect_data_once()

            for circuit in self._circuits:
                circuit.calculate_fitness()
                self.__logger.info(f"{circuit} pulses: {circuit._data}")

            self.__population_bistream_sum = np.zeros(self.__population_bistream_sum.size)
            for circuit in self._circuits:
                # If evaluate returns true, then a circuit has surpassed
                # the threshold and we are done.

                # fitness = circuit.get_fitness()
                fitness = circuit.get_fitness()

                # Save off various circuit metrics
                if self.__config.get_simulation_mode() != 'FULLY_SIM':
                    circuit.set_file_attribute("fitness", str(fitness))
                    if self.__config.is_pulse_count():
                        circuit.set_file_attribute("pulse_count", str(circuit.get_extra_data('pulses')))
                # Commented out for now while we test
                # Pretty sure this was originally for pulse count only, leaving it commented out since things are working right now
                '''if fitness > self.__config.get_randomize_threshold():
                    self.__logger.event(1, "{} fitness: {}".format(circuit, fitness))
                    return'''
                reevaulated_circuits.add(circuit)

                #add the circuit's bistream to our population sum - for diversity calculation and visualization
                if self.__config.get_simulation_mode() != 'FULLY_SIM':
                    self.__population_bistream_sum += circuit.get_bitstream()
                print("sat")

            epoch_time = time() - start
            self._circuits = reevaulated_circuits

            if self.__speedtest:
                fitness_sum = sum(c.get_fitness() for c in self._circuits)
                avg_fitness = fitness_sum / len(self._circuits)
                with open("workspace/speedtest.csv", "a") as f:
                    f.write(f"{self.get_current_epoch()},{epoch_time:.4f},{self._circuits[0].get_fitness():.6f},{avg_fitness:.6f}\n")

            # If one of the new Circuits has a higher fitness than our
            # recorded best, make it the recorded best.
            best_circuit_info = self.get_overall_best_circuit_info()
            self.__logger.event(2, "Best circuit info", best_circuit_info.fitness)
            self.__logger.event(2, "Circuit 0 info",
                             self._circuits[0].get_fitness())

            if self._circuits[0].get_fitness() > best_circuit_info.fitness:
                self.__overall_best_circuit_info = CircuitInfo(
                    str(self._circuits[0]),
                    self._circuits[0].get_fitness()
                )
                self.__best_epoch = self.get_current_epoch()
                # Copy this circuit to the best file
                if isinstance(self._circuits[0], FileBasedCircuit):
                    copyfile(self._circuits[0].get_hardware_file_path(), self.__config.get_best_file())

                # For tone discriminator experiments, update the best waveform and best state data
                # Each file will contain all sampled data points from the new best circuit
                if (self.__config.get_fitness_func() == "TONE_DISCRIMINATOR"):
                    with open("workspace/bestwaveformlivedata.log", "w+") as waveLive:
                        waveLive.write("NEW BEST BELOW: " + str(self._circuits[0]) + " in gen " + str(self.get_current_epoch()) + "\n")
                        i = 1
                        for points in self._circuits[0].get_waveform_td():
                            waveLive.write(str(i) + ", " + str(points) + "\n")
                            i += 1
                    with open("workspace/beststatelivedata.log", "w+") as stateLive:
                        stateLive.write("NEW BEST BELOW: " + str(self._circuits[0]) + " in gen " + str(self.get_current_epoch()) + "\n")
                        i = 1
                        for points in self._circuits[0].get_state_td():
                            stateLive.write(str(i) + ", " + str(points) + "\n")
                            i += 1

                self.__logger.event(2, "New best found")

            # Write waveform data for variance experiments (used by live waveform plot)
            # Written every generation so the plot always shows the current best's waveform
            waveform = self._circuits[0].get_waveform()
            if waveform and self.__config.get_fitness_func() == "VARIANCE":
                with open("workspace/waveformlivedata.log", "w+") as waveLive:
                    for i, point in enumerate(waveform, 1):
                        waveLive.write(f"{i}, {point}\n")

            self.__logger.log_generation(self, epoch_time)
            # The circuits that are protected from randomization

            new_circuits = self.__run_selection(self._circuits)
            self._circuits = SortedKeyList(new_circuits, key=lambda ckt: -1 * ckt.get_fitness())

            self.__write_to_livedata()
            self.__next_epoch()

            if self.__config.using_transfer_interval():
                if self.__current_epoch % self.__config.get_transfer_interval() == 0:
                    pass
                    # self.__microcontroller.switch_fpga()
                    # TODO


        # We have finished evolution! Lets quickly re-evaluate the top circuit, since it
        # will then output its waveform
        if not is_pulse_func(self.__config):
            self.__eval_circuit_once(self._circuits[0])
        # Also, log the name of the top circuit
        self.__logger.event(1, "Top Circuit in Final Generation:", self._circuits[0])

    def __write_to_livedata(self):
        """
        Runs each generation to write data to files used to store data needed for Live plots (PlotEvolutionLive.py)
        """
        fitness_sum = 0
        for c in self._circuits:
            fitness_sum = fitness_sum + c.get_fitness()

        diversity = self.__run_diversity(self._circuits)

        # Write the generation data (avg/best/worst fitness, etc) to file
        if self.get_current_epoch() > 0:
            with open("workspace/bestlivedata.log", "a") as liveFile:
                avg = fitness_sum / self.__config.get_population_size()
                # Format: Epoch, Best Fitness, Worst Fitness, Average Fitness, Ovr Best Fitness, Diversity Measure
                liveFile.write("{}, {}, {}, {}, {}, {}\n".format(
                    str(self.get_current_epoch()),
                    str(self._circuits[0].get_fitness()),
                    str(self._circuits[-1].get_fitness()),
                    str(avg),
                    str(self.get_overall_best_circuit_info().fitness),
                    diversity
                ))

        if self.__multiple_populations:
            # Write the population counts to file (i.e. count of circuits from each source population)
            with open("workspace/poplivedata.log", "a") as live_file:
                counts = [0] * self.__num_subpops
                for ckt in self._circuits:
                    population = int(ckt.get_file_attribute('src_population'))
                    counts[population] = counts[population] + 1
                live_file.write(("{} " * self.__num_subpops + "\n").format(*counts))

        if (self.__current_epoch > 0):
            with open("workspace/violinlivedata.log", "a") as live_file:
                fits = []
                for ckt in self._circuits:
                    fits.append(str(ckt.get_fitness()))
                live_file.write(("{}:{}\n").format(self.__current_epoch, ",".join(fits)))

            if self.__config.get_simulation_mode() in ["FULLY_INTRINSIC", "REMOTE"]:
                if not self.__config.is_pulse_func():
                    with open("workspace/heatmaplivedata.log", "a") as live_file2:
                        best = self._circuits[0]
                        if (self.__config.get_fitness_func() == "TONE_DISCRIMINATOR"):
                            # Need a slightly different function for tone discriminator waveform
                            data  = best.get_waveform_td()
                        else:
                            data = best.get_waveform()
                        live_file2.write(("{}:{}\n").format(self.__current_epoch, ",".join(data)))
                else:
                    with open("workspace/pulselivedata.log", "a") as live_file3:
                        data = []
                        for ckt in self._circuits:
                            data.append(str(ckt.get_extra_data('pulses')))
                        live_file3.write(("{}:{}\n").format(self.__current_epoch, ",".join(data)))

            if self.__config.saving_population_bistream():
                if(self.__current_epoch %
                    self.__config.get_population_bistream_save_interval() == 0):
                    with open("workspace/bitstream_avg.log", "a") as live_file4:
                        data = self.get_differing_bits_str()
                        live_file4.write(("{}:{}\n").format(self.__current_epoch, data))

            # TODO: Re-enable this. Temporarily disabled in case files get too large
            #self.__save_generation()

    def __save_generation(self):
        """
        Saves the current generation to the generations directory
        Each generation gets its own file

        Saves all modifiable parts of a generation so it can be reconstructed.

        called by __write_to_livedata(self)
        """
        gen_lines = []
        # At the top, add the necessary config params such as routing and accessed columns
        gen_lines.append(self.__config.get_routing_type())
        gen_lines.append(','.join(self.__config.get_accessed_columns()))
        # Now, add the bitstream for each circuit on its own line
        # We want the circuits in number order though
        sorted_by_index = SortedKeyList(
            key=lambda ckt: ckt.get_index()
        )
        for ckt in self._circuits:
            sorted_by_index.add(ckt)
        # Now add each circuit
        for ckt in sorted_by_index:
            bitstream = ckt.get_intrinsic_modifiable_bitstream()
            bitstring = ''.join(bitstream)
            gen_lines.add(bitstring)
        # Now actually write the file
        path = self.__config.get_generations_directory().joinpath('gen' + str(self.__current_epoch) + '.log')
        with open(path, 'w') as f:
            f.writelines(gen_lines)

        if (self.__current_epoch > 0):
            with open("workspace/heatmaplivedata.log", "a") as live_file:
                best = self._circuits[0]
                if (self.__config.get_fitness_func() == "TONE_DISCRIMINATOR"):
                    # Need a slightly different function for tone discriminator waveform
                    live_file.write(("{}:{}\n").format(self.__current_epoch, ",".join(best.get_waveform_td())))
                else:
                    live_file.write(("{}:{}\n").format(self.__current_epoch, ",".join(best.get_waveform())))

    # SECTION Getters.
    def get_current_best_circuit(self):
        """
        Gets the circuit in the current generation with the highest fitness

        Returns
        -------
        Circuit
            Returns the best circuit in population.
        """
        return self._circuits[0]

    def get_overall_best_circuit_info(self):
        """
        Returns the information of the circuit with the highest fitness throughout the run

        Returns
        -------
        CircuitInfo
            Returns the info object for the overall best circuit throughout the run.
        """
        return self.__overall_best_circuit_info

    def get_current_epoch(self):
        """
        Returns the generation number

        Returns
        -------
        int
            Returns the generation number of the current evolution.
        """
        return self.__current_epoch

    def get_best_epoch(self):
        """
        Returns the generation number that contained the circuit with the highest fitness

        Returns
        -------
        int
            Generation number that hat the circuit with the highest fitness
        """
        return self.__best_epoch

    # SECTION Miscellaneous helper functions.

    def get_differing_bits_str(self):
        """
        Returns an ASCII string that represents the number of circuits with a 1 at each bit in the bitstream
        Returns
        -------
        str
            The number of circuits with a 1 at each bit in the bitstream

        """
        s = ""
        for bit in self.__population_bistream_sum:
            s += chr(int(bit)+32)
        return s
