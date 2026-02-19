from config_improved import TileDirection
import re
import pprint

directions = {
    "neigh_op_top_0": TileDirection.TOP,
    "neigh_op_tnl_0": TileDirection.TNL,
    "neigh_op_lft_0": TileDirection.LFT,
    "neigh_op_bnl_0": TileDirection.BNL,
    "neigh_op_bot_0": TileDirection.BOT,
    "neigh_op_bnr_0": TileDirection.BNR,
    "neigh_op_rgt_0": TileDirection.RGT,
    "neigh_op_tnr_0": TileDirection.TNR,
}

INPUT_COVERAGE = {
    0: [TileDirection.BOT, TileDirection.TOP, TileDirection.LFT, TileDirection.BNR],
    1: [TileDirection.BOT, TileDirection.TOP, TileDirection.LFT, TileDirection.BNR],
    2: [TileDirection.RGT, TileDirection.BNL, TileDirection.TNL, TileDirection.TNR],
    3: [TileDirection.RGT, TileDirection.BNL, TileDirection.TNL, TileDirection.TNR],
}

RAM_INPUTS = [TileDirection.TNL, TileDirection.LFT, TileDirection.BNL]

tiles = {}

if __name__ == "__main__":
    with open("chipdb", "r") as f:
        lines = []
        time_since_lut = 5
        time_since_ram = 5
        for line in f:
            lines.append(line)
            time_since_lut += 1
            time_since_ram += 1
            if "lutff_0/out" in line:
                time_since_lut = 0
            elif "ram/RDATA_0" in line or "ram/RDATA_8" in line:
                time_since_ram = 0
            if time_since_lut == 4 or time_since_ram == 4:
                for l in lines[-9:]:
                    coords = re.match(r"^(\d{1,2}) (\d{1,2})", l).group().strip() if re.match(r"^(\d{1,2}) (\d{1,2})", l) else None
                    direction = l.replace(coords, "").strip() if coords else None
                    if coords and direction and direction in directions:
                        if coords not in tiles:
                            tiles[coords] = {
                                "inputs": [[],[],[],[]],
                                "ram_out": False,
                            }
                        for i in range(4):
                            if directions[direction] in INPUT_COVERAGE[i]:
                                tiles[coords]["inputs"][i].append(TileDirection.RAM if (directions[direction] in RAM_INPUTS and time_since_ram == 4) else directions[direction])
                                
                        tiles[coords]["ram_out"] = (directions[direction] == TileDirection.RGT and time_since_ram == 4)

    pprint.pprint(tiles)