# Node Genotype Layout:
# ----------------
# 0 - 1  | Input 0 (3 bits encoding TileDirection)
# 2 - 3  | Input 1 (3 bits encoding TileDirection)
# 4 - 5  | Input 2 (3 bits encoding TileDirection)
# 6 - 7  | Input 3 (3 bits encoding TileDirection)
# 8 - 27 | LUT Init (20 bits)

# TODO: If a RAM tile separates 2 tiles, use an sp4_h net to connect them.
#       This means setting B1[46] in the left tile and telling the right tile to connect to relevant span

import math
import os
import subprocess
import numpy as np
from dataclasses import dataclass, field
import random
from config_improved import TileDirection, generate_tile
try:
    from bitstream_transfer_test import upload
except ImportError:
    upload = None

@dataclass
class Config:
    lut_size: int = 20
    node_size: int = lut_size + 8
    mutation_rate: float = 0.01
    num_nodes: int = 30
    population_size: int = 10
    generations: int = 10
    board_width: int = 10
    logic_tiles: list[tuple[int, int]] = field(default_factory=lambda: [(c, r) for r in range(1, 31) for c in range(1, 25) if c not in {6, 19}])
    ram_tiles: list[tuple[int, int]] = field(default_factory=lambda: [(c, r) for r in range(1, 31) for c in (6, 19)])
    io_tiles: list[tuple[int, int]] = field(default_factory=lambda: [(c, r) for r in (0, 31) for c in range(1, 25)])
    dsp_tiles: list[tuple[int, int]] = field(default_factory=lambda: [(c, r) for c in (0, 25) for r in list(range(5, 9)) + list(range(10, 14)) + list(range(15, 19)) + list(range(23, 27))])
    ipcon_tiles: list[tuple[int, int]] = field(default_factory=lambda: [(c, r) for c in (0, 25) for r in [1, 2, 3, 4, 9, 14, 19, 20, 21, 22, 27, 28, 29, 30]])
    ram_columns: list = field(default_factory=lambda: [6, 19])
    
# Mapping from 3-bit integer to TileDirection
DIRECTION_MAP = [
    TileDirection.BOT,
    TileDirection.TOP,
    TileDirection.LFT,
    TileDirection.RGT,
    TileDirection.BNL,
    TileDirection.BNR,
    TileDirection.TNL,
    TileDirection.TNR,
]

INPUT_COVERAGE = {
    0: [TileDirection.BOT, TileDirection.TOP, TileDirection.LFT, TileDirection.BNR],
    1: [TileDirection.BOT, TileDirection.TOP, TileDirection.LFT, TileDirection.BNR],
    2: [TileDirection.RGT, TileDirection.BNL, TileDirection.TNL, TileDirection.TNR],
    3: [TileDirection.RGT, TileDirection.BNL, TileDirection.TNL, TileDirection.TNR],
}

def decode_direction(input_num, bits):
    """Convert 3-bit integer (0-7) to TileDirection."""
    if bits < 0 or bits > 7:
        return TileDirection.NULL
    return INPUT_COVERAGE[input_num][bits]

def encode_direction(direction):
    """Convert TileDirection to 3-bit integer (0-7)."""
    try:
        return DIRECTION_MAP.index(direction)
    except ValueError:
        return 0

def decode_genotype(gene):
    """
    Decode a 32-bit gene into tile configuration.

    Returns:
        (input0, input1, input2, input3, lut_init)
    """
    # Extract 3-bit direction encodings
    input0 = decode_direction(0, (gene >> 0) & 0x3)
    input1 = decode_direction(1, (gene >> 2) & 0x3)
    input2 = decode_direction(2, (gene >> 4) & 0x3)
    input3 = decode_direction(3, (gene >> 6) & 0x3)

    # Extract 20-bit LUT init (bits 12-31)
    lut_init = (gene >> 12) & 0xFFFFF

    return input0, input1, input2, input3, lut_init

def generate_tile_from_gene(x, y, gene, output=False, past_ram=False):
    """Generate a tile configuration from a 32-bit gene."""
    input0, input1, input2, input3, lut_init = decode_genotype(gene)
    return generate_tile(x, y, input0, input1, input2, input3, lut_init, output, past_ram)

def generate_asc_config(genotype):
    """
    Generate ASCII bitstream configuration from genotype.

    Args:
        genotype: Array of genes, one per node

    Returns:
        String containing the ASCII bitstream
    """
    
    def blank_io(x, y):
        return f".io_tile {x} {y}\n" + \
                "000000000000000000\n" + \
                "000000110000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000010000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n" + \
                "000000000000000000\n"
    
    def blank_ram(x, y):
        return f".ram{'t' if y % 2 == 0 else 'b'}_tile {x} {y}\n" + "\n".join(["0"*42 for _ in range(16)])

    def blank_logic(x, y):
        return f".logic_tile {x} {y}\n" + "\n".join(["0"*54 for _ in range(16)])

    def blank_dsp(x, y):
        # DSP tiles come in groups of 4: dsp0, dsp1, dsp2, dsp3
        # Pattern: rows 5-8 (0-3), 10-13 (0-3), 15-18 (0-3), 23-26 (0-3)
        if 5 <= y <= 8:
            dsp_type = y - 5
        elif 10 <= y <= 13:
            dsp_type = y - 10
        elif 15 <= y <= 18:
            dsp_type = y - 15
        elif 23 <= y <= 26:
            dsp_type = y - 23
        else:
            dsp_type = 0
        return f".dsp{dsp_type}_tile {x} {y}\n" + "\n".join(["0"*54 for _ in range(16)])

    def blank_ipcon(x, y):
        return f".ipcon_tile {x} {y}\n" + "\n".join(["0"*54 for _ in range(16)])
    
    config = Config()
    asc = ".comment direct routing generated\n.device 5k\n"
    for i in range(len(genotype)):
        x, y = config.logic_tiles[i]
        gene = genotype[i]
        output = ((i+1) % config.board_width == 0)
        past_ram = (x-1) in config.ram_columns
        tile = generate_tile_from_gene(x, y, gene, output, past_ram)
        asc += tile + "\n"
        
    for i in range(len(genotype), len(config.logic_tiles)):
        x, y = config.logic_tiles[i]
        tile = blank_logic(x, y)
        asc += tile + "\n"

    for x, y in config.io_tiles:
        tile = blank_io(x, y)
        asc += tile + "\n"

    for x, y in config.ram_tiles:
        tile = blank_ram(x, y)
        asc += tile + "\n"

    for x, y in config.dsp_tiles:
        tile = blank_dsp(x, y)
        asc += tile + "\n"

    for x, y in config.ipcon_tiles:
        tile = blank_ipcon(x, y)
        asc += tile + "\n"

    return asc

def make_population(size, num_nodes):
    """Create initial random population."""
    population = {}
    for i in range(size):
        genotype = []
        for j in range(num_nodes):
            # Random 32-bit gene
            gene = np.random.randint(0, 2**32, dtype=np.uint32)
            genotype.append(gene)
        population[i] = np.array(genotype, dtype=np.uint32)
    # print(f"Individual 0: {population[0]}")
    return population

def mutate_population(population, rate=0.01):
    """Mutate population by flipping random bits."""
    for i in population:
        genotype = population[i]
        for j in range(len(genotype)):
            # Mutate by flipping random bits
            if np.random.rand() < rate:
                bit_to_flip = np.random.randint(0, 32)
                genotype[j] = genotype[j] ^ (1 << bit_to_flip)
        population[i] = genotype
    print(f"Individual 0 after mutation: {population[0]}")

if __name__ == "__main__":
    config = Config()
    population = make_population(config.population_size, config.num_nodes)
    with open("generated.asc", "w") as f:
         f.write(generate_asc_config(population[0]))

    subprocess.run(
        ["icepack", "generated.asc", "generated.bin"], check=True
    )

    if upload:
        upload()
    
    print(generate_asc_config(population[0]))