import random
import numpy as np

# Customized Algorithm for Initial Scheduling
def initial_scheduling(orders, technicians):
    # Example: Assign orders to technicians based on their expertise and availability
    schedule = {}
    for order in orders:
        suitable_technicians = [tech for tech in technicians if tech['expertise'] >= order['complexity']]
        if suitable_technicians:
            # Assign the first available suitable technician
            tech = suitable_technicians[0]
            schedule[order['id']] = tech['id']
            tech['availability'] -= order['duration']  # Reduce technician's availability
    return schedule

# Fitness function for Genetic Algorithm
def calculate_fitness(schedule, orders, technicians):
    expertise_score = sum([technicians[schedule[order['id']]]['expertise'] for order in orders])
    workload_balance_score = np.std([sum([order['duration'] for order in orders if schedule[order['id']] == tech['id']]) for tech in technicians])
    time_management_score = sum([1 if technicians[schedule[order['id']]]['availability'] >= order['duration'] else -1 for order in orders])

    # Penalties for workload imbalance and expertise mismatch
    penalties = workload_balance_score
    fitness_score = expertise_score + time_management_score - penalties
    return fitness_score

# Genetic Algorithm for Optimization
def genetic_algorithm(orders, technicians, population_size=100, generations=50, crossover_rate=0.8, mutation_rate=0.01):
    # Initialize population with random schedules
    population = [initial_scheduling(orders, technicians) for _ in range(population_size)]

    for generation in range(generations):
        # Calculate fitness for each schedule in the population
        fitness_scores = [calculate_fitness(individual, orders, technicians) for individual in population]

        # Selection: Choose individuals with higher fitness scores
        selected_individuals = [population[i] for i in np.argsort(fitness_scores)[-population_size//2:]]

        # Crossover: Create new offspring by combining pairs of individuals
        offspring = []
        for i in range(population_size//2):
            if random.random() < crossover_rate:
                parent1, parent2 = random.sample(selected_individuals, 2)
                child = crossover(parent1, parent2, orders)
                offspring.append(child)

        # Mutation: Apply random changes to some individuals
        for individual in offspring:
            if random.random() < mutation_rate:
                mutate(individual, orders)

        # Create new population by combining selected individuals and offspring
        population = selected_individuals + offspring

    # Return the best schedule from the final population
    best_individual = max(population, key=lambda ind: calculate_fitness(ind, orders, technicians))
    return best_individual

# Helper function for crossover (combines two parent schedules)
def crossover(parent1, parent2, orders):
    child = {}
    for order in orders:
        if random.random() > 0.5:
            child[order['id']] = parent1[order['id']]
        else:
            child[order['id']] = parent2[order['id']]
    return child

# Helper function for mutation (randomly reassigns one task)
def mutate(individual, orders):
    order_to_mutate = random.choice(orders)
    available_technicians = [tech['id'] for tech in technicians]
    individual[order_to_mutate['id']] = random.choice(available_technicians)

# Example usage
orders = [{'id': 1, 'complexity': 3, 'duration': 5}, {'id': 2, 'complexity': 2, 'duration': 3}, ...]
technicians = [{'id': 1, 'expertise': 4, 'availability': 10}, {'id': 2, 'expertise': 3, 'availability': 8}, ...]

# Step 1: Initial scheduling with customized algorithm
initial_schedule = initial_scheduling(orders, technicians)

# Step 2: Optimize the schedule with genetic algorithm
optimized_schedule = genetic_algorithm(orders, technicians)
print("Optimized Schedule:", optimized_schedule)
