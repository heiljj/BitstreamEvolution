"""
iCE40 HX1K Logic Cell 0 Configuration Data

This module provides configuration data for routing neighbor tile signals
to Logic Cell 0 (lutff_0) inputs in tile (6,9).

Configuration requires two stages:
1. Configure local_g nets to receive from neighbor tiles (neigh_op_*)
2. Configure LUT inputs to receive from local_g nets
"""

import copy
import argparse
import sys
from enum import Enum

class TileDirection(Enum):
    """Enum for the 8 tiles surrounding the center tile."""
    BOT = 'bot'      # bottom
    TOP = 'top'      # top
    LFT = 'lft'      # left
    RGT = 'rgt'      # right
    BNL = 'bnl'      # bottom-left
    BNR = 'bnr'      # bottom-right
    TNL = 'tnl'      # top-left
    TNR = 'tnr'      # top-right
    RAM = 'ram'      # RAM tile connection
    NULL = None      # no neighbor

# =============================================================================
# STAGE 1: Local Net Configuration (local_g mux)
# =============================================================================
# Format: local_net_config[net_name][neighbor_direction] = (bits, bit_positions)

LOCAL_NET_CONFIG = {
    # Input 0 recommended nets
    'local_g0_0': {
        'bit_positions': ['B0[14]', 'B1[14]', 'B1[15]', 'B1[16]', 'B1[17]'],
        'neighbors': {
            'bot': [0, 0, 1, 0, 1],  # neigh_op_bot_0
            'top': [0, 1, 1, 0, 1],  # neigh_op_top_0
            'lft': [1, 0, 1, 0, 1],  # neigh_op_lft_0
            'bnr': [1, 1, 0, 0, 1],  # neigh_op_bnr_0
        }
    },
    
    # Input 1 recommended nets
    'local_g1_0': {
        'bit_positions': ['B4[14]', 'B5[14]', 'B5[15]', 'B5[16]', 'B5[17]'],
        'neighbors': {
            'bot': [0, 0, 1, 0, 1],  # neigh_op_bot_0
            'top': [0, 1, 1, 0, 1],  # neigh_op_top_0
            'lft': [1, 0, 1, 0, 1],  # neigh_op_lft_0
            'bnr': [1, 1, 0, 0, 1],  # neigh_op_bnr_0
        }
    },
    
    # Input 2 recommended nets
    'local_g2_0': {
        'bit_positions': ['B8[14]', 'B9[14]', 'B9[15]', 'B9[16]', 'B9[17]'],
        'neighbors': {
            'rgt': [1, 0, 1, 0, 1],  # neigh_op_rgt_0
            'bnl': [1, 1, 0, 0, 1],  # neigh_op_bnl_0
            'tnl': [0, 1, 1, 0, 1],  # neigh_op_tnl_0
            'tnr': [0, 0, 1, 0, 1],  # neigh_op_tnr_0
            'ram': [0, 1, 1, 1, 1],  # Special case for RAM tile connection
        }
    },
    
    # Input 3 recommended nets
    'local_g3_0': {
        'bit_positions': ['B12[14]', 'B13[14]', 'B13[15]', 'B13[16]', 'B13[17]'],
        'neighbors': {
            'rgt': [1, 0, 1, 0, 1],  # neigh_op_rgt_0
            'bnl': [1, 1, 0, 0, 1],  # neigh_op_bnl_0
            'tnl': [0, 1, 1, 0, 1],  # neigh_op_tnl_0
            'tnr': [0, 0, 1, 0, 1],  # neigh_op_tnr_0
            'ram': [0, 1, 1, 1, 1],  # Special case for RAM tile connection
        }
    },
}

# =============================================================================
# STAGE 2: LUT Input Configuration (LUT input mux)
# =============================================================================
# Format: lut_input_config[input_num][local_net] = (bits, bit_positions)

LUT_INPUT_CONFIG = {
    # Input 0
    0: {
        'bit_positions': ['B0[26]', 'B1[26]', 'B1[27]', 'B1[28]', 'B1[29]'],
        'sources': {
            'local_g0_0': [0, 0, 0, 0, 1],
            'local_g2_0': [0, 0, 0, 1, 1],
            'local_g1_1': [0, 0, 1, 0, 1],
            'local_g3_1': [0, 0, 1, 1, 1],
            'local_g0_2': [0, 1, 0, 0, 1],
            'local_g2_2': [0, 1, 0, 1, 1],
            'local_g1_3': [0, 1, 1, 0, 1],
            'local_g3_3': [0, 1, 1, 1, 1],
            'local_g0_4': [1, 0, 0, 0, 1],
            'local_g2_4': [1, 0, 0, 1, 1],
            'local_g1_5': [1, 0, 1, 0, 1],
            'local_g3_5': [1, 0, 1, 1, 1],
            'local_g0_6': [1, 1, 0, 0, 1],
            'local_g2_6': [1, 1, 0, 1, 1],
            'local_g1_7': [1, 1, 1, 0, 1],
            'local_g3_7': [1, 1, 1, 1, 1],
        }
    },
    
    # Input 1
    1: {
        'bit_positions': ['B0[27]', 'B0[28]', 'B0[29]', 'B0[30]', 'B1[30]'],
        'sources': {
            'local_g0_1': [0, 0, 1, 0, 0],
            'local_g0_3': [0, 0, 1, 0, 1],
            'local_g0_5': [0, 0, 1, 1, 0],
            'local_g0_7': [0, 0, 1, 1, 1],
            'local_g2_1': [0, 1, 1, 0, 0],
            'local_g2_3': [0, 1, 1, 0, 1],
            'local_g2_5': [0, 1, 1, 1, 0],
            'local_g2_7': [0, 1, 1, 1, 1],
            'local_g1_0': [1, 0, 1, 0, 0],
            'local_g1_2': [1, 0, 1, 0, 1],
            'local_g1_4': [1, 0, 1, 1, 0],
            'local_g1_6': [1, 0, 1, 1, 1],
            'local_g3_0': [1, 1, 1, 0, 0],
            'local_g3_2': [1, 1, 1, 0, 1],
            'local_g3_4': [1, 1, 1, 1, 0],
            'local_g3_6': [1, 1, 1, 1, 1],
        }
    },
    
    # Input 2
    2: {
        'bit_positions': ['B0[35]', 'B1[32]', 'B1[33]', 'B1[34]', 'B1[35]'],
        'sources': {
            'local_g0_0': [0, 1, 0, 0, 0],
            'local_g0_2': [0, 1, 0, 0, 1],
            'local_g1_1': [0, 1, 0, 1, 0],
            'local_g1_3': [0, 1, 0, 1, 1],
            'local_g2_0': [0, 1, 1, 0, 0],
            'local_g2_2': [0, 1, 1, 0, 1],
            'local_g3_1': [0, 1, 1, 1, 0],
            'local_g3_3': [0, 1, 1, 1, 1],
            'local_g0_4': [1, 1, 0, 0, 0],
            'local_g0_6': [1, 1, 0, 0, 1],
            'local_g1_5': [1, 1, 0, 1, 0],
            'local_g1_7': [1, 1, 0, 1, 1],
            'local_g2_4': [1, 1, 1, 0, 0],
            'local_g2_6': [1, 1, 1, 0, 1],
            'local_g3_5': [1, 1, 1, 1, 0],
            'local_g3_7': [1, 1, 1, 1, 1],
        }
    },
    
    # Input 3
    3: {
        'bit_positions': ['B0[31]', 'B0[32]', 'B0[33]', 'B0[34]', 'B1[31]'],
        'sources': {
            'carry_in_mux': [0, 1, 0, 0, 0],
            'local_g0_3': [0, 1, 0, 0, 1],
            'local_g1_0': [0, 1, 0, 1, 0],
            'local_g1_2': [0, 1, 0, 1, 1],
            'local_g2_1': [0, 1, 1, 0, 0],
            'local_g2_3': [0, 1, 1, 0, 1],
            'local_g3_0': [0, 1, 1, 1, 0],
            'local_g3_2': [0, 1, 1, 1, 1],
            'local_g0_5': [1, 1, 0, 0, 0],
            'local_g0_7': [1, 1, 0, 0, 1],
            'local_g1_4': [1, 1, 0, 1, 0],
            'local_g1_6': [1, 1, 0, 1, 1],
            'local_g2_5': [1, 1, 1, 0, 0],
            'local_g2_7': [1, 1, 1, 0, 1],
            'local_g3_4': [1, 1, 1, 1, 0],
            'local_g3_6': [1, 1, 1, 1, 1],
        }
    },
}

# =============================================================================
# Recommended Configuration for 8-Neighbor Connectivity
# =============================================================================

RECOMMENDED_NETS = {
    0: ['local_g0_0'],
    1: ['local_g1_0'],
    2: ['local_g2_0'],
    3: ['local_g3_0'],
}

# Neighbor tile coordinates relative to tile (6,9)
NEIGHBOR_COORDS = {
    'bot': (6, 8),   # bottom
    'top': (6, 10),  # top
    'lft': (5, 9),   # left
    'rgt': (7, 9),   # right
    'bnl': (5, 8),   # bottom-left
    'bnr': (7, 8),   # bottom-right
    'tnl': (5, 10),  # top-left
    'tnr': (7, 10),  # top-right
}

# Which neighbors each net group can reach
NET_GROUP_COVERAGE = {
    'g0': ['bot', 'top', 'lft', 'bnr'],  # local_g0_* and local_g1_*
    'g1': ['bot', 'top', 'lft', 'bnr'],
    'g2': ['rgt', 'bnl', 'tnl', 'tnr'],  # local_g2_* and local_g3_*
    'g3': ['rgt', 'bnl', 'tnl', 'tnr'],
}

# =============================================================================
# Helper Functions
# =============================================================================

def parse_bit_position(bit_pos):
    """
    Parse bit position string like 'B0[14]' into (bank, bit).
    
    Args:
        bit_pos: String like 'B0[14]' or 'B1[26]'
    
    Returns:
        tuple: (bank, bit) as integers
    
    Example:
        >>> parse_bit_position('B0[14]')
        (0, 14)
    """
    import re
    match = re.match(r'B(\d+)\[(\d+)\]', bit_pos)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    raise ValueError(f"Invalid bit position format: {bit_pos}")


def get_local_net_config(net_name, neighbor):
    """
    Get configuration bits for routing a neighbor to a local net.
    
    Args:
        net_name: Local net name (e.g., 'local_g0_0')
        neighbor: Neighbor direction (e.g., 'bot', 'top', 'lft', 'rgt', etc.)
    
    Returns:
        list: List of tuples [(bank, bit, value), ...]
    
    Example:
        >>> get_local_net_config('local_g0_0', 'bot')
        [(0, 14, 0), (1, 14, 0), (1, 15, 1), (1, 16, 0), (1, 17, 1)]
    """
    if net_name not in LOCAL_NET_CONFIG:
        raise ValueError(f"Unknown local net: {net_name}")
    
    net_config = LOCAL_NET_CONFIG[net_name]
    
    if neighbor not in net_config['neighbors']:
        raise ValueError(f"Net {net_name} cannot reach neighbor {neighbor}")
    
    bit_values = net_config['neighbors'][neighbor]
    bit_positions = net_config['bit_positions']
    
    result = []
    for bit_pos, value in zip(bit_positions, bit_values):
        bank, bit = parse_bit_position(bit_pos)
        result.append((bank, bit, value))
    
    return result


def get_lut_input_config(input_num, net_name):
    """
    Get configuration bits for routing a local net to a LUT input.
    
    Args:
        input_num: LUT input number (0-3)
        net_name: Local net name (e.g., 'local_g0_0')
    
    Returns:
        list: List of tuples [(bank, bit, value), ...]
    
    Example:
        >>> get_lut_input_config(0, 'local_g0_0')
        [(0, 26, 0), (1, 26, 0), (1, 27, 0), (1, 28, 0), (1, 29, 1)]
    """
    if input_num not in LUT_INPUT_CONFIG:
        raise ValueError(f"Invalid input number: {input_num}")
    
    input_config = LUT_INPUT_CONFIG[input_num]
    
    if net_name not in input_config['sources']:
        raise ValueError(f"Net {net_name} cannot connect to input {input_num}")
    
    bit_values = input_config['sources'][net_name]
    bit_positions = input_config['bit_positions']
    
    result = []
    for bit_pos, value in zip(bit_positions, bit_values):
        bank, bit = parse_bit_position(bit_pos)
        result.append((bank, bit, value))
    
    return result


def get_full_path_config(input_num, neighbor):
    """
    Get complete configuration for routing a neighbor to a LUT input.

    This handles both stages:
    1. Configure appropriate local_g net to receive from neighbor
    2. Configure LUT input to receive from that local_g net

    Args:
        input_num: LUT input number (0-3)
        neighbor: TileDirection enum or None

    Returns:
        dict: {
            'local_net': net name used,
            'local_net_config': [(bank, bit, value), ...],
            'lut_input_config': [(bank, bit, value), ...]
        }
        or None if neighbor is TileDirection.NULL or None

    Example:
        >>> config = get_full_path_config(0, TileDirection.BOT)
        >>> print(config['local_net'])
        'local_g0_0'
    """
    if neighbor is None or neighbor == TileDirection.NULL:
        return None

    if input_num not in RECOMMENDED_NETS:
        raise ValueError(f"Invalid input number: {input_num}")

    # Convert enum to string value
    neighbor_str = neighbor.value if isinstance(neighbor, TileDirection) else neighbor

    # Determine which net can reach this neighbor
    net_candidates = RECOMMENDED_NETS[input_num]

    selected_net = None
    for net_name in net_candidates:
        if neighbor_str in LOCAL_NET_CONFIG[net_name]['neighbors']:
            selected_net = net_name
            break

    if selected_net is None:
        raise ValueError(f"No recommended net for input {input_num} can reach {neighbor_str}")

    return {
        'local_net': selected_net,
        'local_net_config': get_local_net_config(selected_net, neighbor_str),
        'lut_input_config': get_lut_input_config(input_num, selected_net),
    }

def generate_tile(x, y, input0, input1, input2, input3, lut_init=0, output=False, past_ram=False):
    """
    Generate a new tile configuration from scratch given 4 input configurations.

    Args:
        x: X coordinate of the tile
        y: Y coordinate of the tile
        input0: TileDirection enum or None for LUT input 0
        input1: TileDirection enum or None for LUT input 1
        input2: TileDirection enum or None for LUT input 2
        input3: TileDirection enum or None for LUT input 3
        lut_init: 20-bit number for LUT initialization (default: 0)
                  Bits are mapped to B0[36]-B0[45] and B1[36]-B1[45]
        output: If True, connects lutff_0/out to a span12 net (default: False)

    Returns:
        list: 16-element list representing the tile configuration,
              each element is a list of 54 bits.

    Example:
        >>> tile = generate_tile(TileDirection.BNR, TileDirection.BOT, TileDirection.LFT, TileDirection.RGT)
        >>> tile = generate_tile(TileDirection.BNR, TileDirection.BOT, TileDirection.LFT, TileDirection.RGT, lut_init=0xABCDE)
    """
    tile = [['0']*54 for _ in range(16)]
    tile = modify_tile(tile, input0, input1, input2, input3, lut_init, output, past_ram)
    tile_str = f".logic_tile {x} {y}\n"
    for _ in tile:
        tile_str += ''.join(_) + '\n'
    return tile_str


def modify_tile(tile, input0, input1, input2, input3, lut_init=0, output=False, past_ram=False):
    """
    Generate a full tile configuration given 4 input configurations.

    Args:
        tile: 16-element list representing the tile configuration,
              each element is a list of 54 bits.
        input0: TileDirection enum or None for LUT input 0
        input1: TileDirection enum or None for LUT input 1
        input2: TileDirection enum or None for LUT input 2
        input3: TileDirection enum or None for LUT input 3
        lut_init: 20-bit number for LUT initialization (default: 0)
                  Bits are mapped to B0[36]-B0[45] and B1[36]-B1[45]

    Returns:
        list: Modified 16-element list representing the tile configuration,
              each element is a list of 54 bits.
    """
    inputs = [input0, input1, input2, input3]

    for input_num, neighbor in enumerate(inputs):
        if neighbor is None or neighbor == TileDirection.NULL:
            continue
        
        if past_ram and (neighbor == TileDirection.BNL or neighbor == TileDirection.TNL):
            neighbor = TileDirection.RAM

        config = get_full_path_config(input_num, neighbor)
        if config is None:
            continue

        # Apply local net configuration
        for bank, bit, value in config['local_net_config']:
            tile[bank][bit] = str(value)

        # Apply LUT input configuration
        for bank, bit, value in config['lut_input_config']:
            tile[bank][bit] = str(value)

    # Apply LUT initialization bits
    # Map 20-bit lut_init to B0[36]-B0[45] (bits 0-9) and B1[36]-B1[45] (bits 10-19)
    if lut_init != 0:
        # Bits 0-9: B0[36]-B0[45]
        for i in range(10):
            bit_value = (lut_init >> i) & 1
            tile[0][36 + i] = str(bit_value)

        # Bits 10-19: B1[36]-B1[45]
        for i in range(10):
            bit_value = (lut_init >> (10 + i)) & 1
            tile[1][36 + i] = str(bit_value)
            
    if output:
        tile[0][47] = '1'
    
    tile[1][46] = '1' # Connect to sp4_h net for crossing RAM tiles

    return tile

def print_tile(tile):
    """
    Print the tile configuration in a readable format.
    
    Args:
        tile: 16-element list representing the tile configuration,
              each element is a string of 54 bits.
    """
    for bank in tile:
        print(''.join(bank))

if __name__ == '__main__':
    tile = [['0']*54 for _ in range(16)]
    print("iCE40 Configuration Data Module")
    print("=" * 70)

    # Configure the 4 LUT inputs with their respective neighbor tiles
    tile = modify_tile(tile,
                       TileDirection.BNR,  # input 0
                       TileDirection.BOT,  # input 1
                       TileDirection.LFT,  # input 2
                       TileDirection.RGT)  # input 3

    print_tile(tile)