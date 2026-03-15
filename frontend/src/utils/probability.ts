export interface EvScenario {
    id: string;
    description: string;
    probability: number; // 0.0 to 1.0
    payoff: number; // raw value return (e.g. 1500 for a $1500 win, -500 for a $500 loss)
}

export function calculateEV(scenarios: EvScenario[]): number {
    let ev = 0;
    for (const s of scenarios) {
        ev += s.probability * s.payoff;
    }
    return ev;
}

export function validateProbabilities(scenarios: EvScenario[]): boolean {
    const sum = scenarios.reduce((acc, s) => acc + s.probability, 0);
    // Allow for small floating point errors, e.g. 0.99999999999
    return Math.abs(sum - 1.0) < 0.001;
}

export function calculateKellyFraction(
    winProbability: number,
    winReward: number,
    lossPenalty: number
): number {
    if (lossPenalty === 0 || winReward === 0) return 0;
    if (winProbability <= 0) return 0;
    if (winProbability >= 1) return 1;

    // Standard Kelly criterion formula: f* = p - (q / b)
    // p = probability of a win
    // q = probability of a loss (1 - p)
    // b = proportion of the bet gained with a win. e.g. If you bet $10 to win $20 (profit of $10), b = 1
    // Notice that this assumes a $1 loss is 1 unit.
    // If win is variable, b = Expected Return / Expected Loss. 
    // Wait, simple Kelly is: f* = (p * b - q) / b  where b = win fraction / loss fraction.

    const b = winReward / Math.abs(lossPenalty);
    const q = 1 - winProbability;
    
    let f = (winProbability * b - q) / b;
    
    return Math.max(0, f); // Can't bet less than 0
}
