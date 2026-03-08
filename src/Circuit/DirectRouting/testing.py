import shutil
from simulation import Config, make_population, generate_asc_config

SEED_PATH = "ice27_only_no_logic.asc"
OUT_PATH = "different_genome_example.asc"
X_SIZE = 12
Y_SIZE = 12
# top left corner of tile
LOCATIONS = [(7, 29), (7, 13)]

pop_size = len(LOCATIONS)
node_size = X_SIZE * Y_SIZE

population = make_population(pop_size, node_size)

shutil.copyfile(SEED_PATH, OUT_PATH)

for i, pos in enumerate(LOCATIONS):
    config = Config(logic_tiles=[(x, y) for x in range(pos[0], pos[0] + X_SIZE) for y in range(pos[1] - Y_SIZE + 1, pos[1] + 1)])
    out = (generate_asc_config(population[i], config, OUT_PATH))
    with open(OUT_PATH, "w") as f:
        f.write(out)
