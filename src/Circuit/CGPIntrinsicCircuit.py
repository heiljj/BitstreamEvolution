from pathlib import Path
from Circuit.FileBasedCircuit import FileBasedCircuit
from Circuit.FitnessFunction import FitnessFunction
from time import sleep
from subprocess import run
import Config
import Microcontroller
import Logger
from Circuit.DirectRouting.simulation import make_individual
from Circuit.DirectRouting.simulation import generate_asc_config
import random
import pickle
from pathlib import PosixPath
from mmap import mmap

RUN_CMD = "iceprog"
COMPILE_CMD = "icepack"

class CGPIntrinsicCircuit(FileBasedCircuit):
    """
    No longer an abstract class. Represents circuits that get uploaded to the physical FPGA
    The fitness strategy provided is used to evaluate the circuits
    """
    def __init__(self, index: int, filename: str, config: Config, template: Path, rand, logger: Logger, microcontroller: Microcontroller, fitness_func: FitnessFunction):
        FileBasedCircuit.__init__(self, index, filename, config, template, rand, logger)
        self._fitness_func = fitness_func
        self._extra_data = dict()
        self._fitness_func.attach(self._data_filepath, microcontroller, self._config, self._extra_data)
        seed = make_individual(35)
        self._log_event(0,seed)
        with open(self._hardware_filepath, 'wb') as f:
            pickle.dump(seed, f)
        self._attributes = {}

    def evaluate_once(self):
        self.clear_data()
        self.collect_data_once()
        self.calculate_fitness()

    def _get_measurement(self):
        return self._fitness_func.get_measurements()

    def _calculate_fitness(self) -> float:
        print("calcfitness")
        return self._fitness_func.calculate_fitness(self._data)

    def upload(self):
        self.__run()

    def get_waveform(self):
        return self._fitness_func.get_waveform()

    def get_extra_data(self, key):
        return self._extra_data[key]
    
    # TODO: Make this convert from CGP to ASC
    def _compile(self):
        """
        Compile circuit ASC file to a BIN file for hardware upload.
        """
        self._log_event(2, "Compiling", self, "with icepack...")

        # Ensure the file backing the mmap is up to date with the latest
        # changes to the mmap.
        self._hardware_file.flush()
        
        with open(self._hardware_filepath, "rb") as f:
            bitstream = pickle.load(f)
        
        asc = generate_asc_config(bitstream)
        ascfile = self._hardware_filepath.with_stem(f"{self._hardware_filepath.stem}{"asc"}")
        with open(ascfile, "w") as f:
            f.write(asc)
        
        compile_command = [
            COMPILE_CMD,
            ascfile,
            self._bitstream_filepath
        ]
        run(compile_command)

        self._log_event(2, "Finished compiling", self)

    def __run(self):
        """
        Compiles and uploads the compiled circuit and runs it on the FPGA
        """
        
        self._compile()

        cmd_str = [
            RUN_CMD,
            self._bitstream_filepath,
            "-d",
            self._config.get_fpga()
        ]
        print(cmd_str)
        run(cmd_str)
        sleep(1)

        # if switching fpgas every sample, need to upload to the second fpga also
        if self._config.get_transfer_sample():
            cmd_str = [
                RUN_CMD,
                self._bitstream_filepath,
                "-d",
                self._config.get_fpga2()
            ]
            print(cmd_str)
            run(cmd_str)
            sleep(1)

    def mutate(self):
        prob = self._config.get_mutation_probability()
        with open(self._hardware_filepath, "rb") as f:
            bitstream = pickle.load(f)
        num_bits = bitstream.dtype.itemsize * 8
        for i in range(len(bitstream)):
            for bit in range(num_bits):
                if random.random() < prob:
                    bitstream[i] ^= (1 << bit)
        with open(self._hardware_filepath, "wb") as f:
            pickle.dump(bitstream, f)

    def get_file_attribute(self, attribute):
        '''
        Returns the value of the stored attribute for this Circuit
        Circuits are capable of storing string name-value pairs in their hardware file, for purposes such as
        tracking most recently-evaluated fitness of a Circuit

        Parameters
        ----------
        attrbute : str
            The name of the attribute of this circuit you want

        Returns
        -------
        str
            The value of the attribute
        '''
        print("Get file attribute")
        if attribute in self._attributes:
            return self._attributes[attribute]
        return ""

    def set_file_attribute(self, attribute, value):
        '''
        Sets this Circuit's file attribute to the specified value
        Circuits are capable of storing string name-value pairs in their hardware file, for purposes such as
        tracking most recently-evaluated fitness of a Circuit

        Parameters
        ----------
        attribute : str
            The name of the attribute to modify
        value : str
            The value to assign to the attribute
        '''
        print("Set file attribute")
        self._attributes[attribute] = value