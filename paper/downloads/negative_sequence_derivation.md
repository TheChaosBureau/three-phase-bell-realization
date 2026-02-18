# Negative Sequence Impact on Power Boundaries

## Mathematical Derivation

### Current with Both Positive and Negative Sequence

```
I_a(t) = I_p⁺ sin(ωt + θ⁺) + I_p⁻ sin(ωt + θ⁻)
I_b(t) = I_p⁺ sin(ωt + θ⁺ - 2π/3) + I_p⁻ sin(ωt + θ⁻ + 2π/3)
I_c(t) = I_p⁺ sin(ωt + θ⁺ + 2π/3) + I_p⁻ sin(ωt + θ⁻ - 2π/3)
```

Note: Negative sequence has **opposite phase rotation** (CW instead of CCW)

### Line-to-Neutral Power with Both Sequences

Each phase power:
```
p_a(t) = V_p sin(ωt) · [I_p⁺ sin(ωt + θ⁺) + I_p⁻ sin(ωt + θ⁻)]
```

Using the product-to-sum identity on each term separately:

**Positive sequence contribution:**
```
p_a⁺(t) = (V_p I_p⁺ / 2)[cos(θ⁺) - cos(2ωt + θ⁺)]
```

**Negative sequence contribution:**
```
p_a⁻(t) = (V_p I_p⁻ / 2)[cos(θ⁻) - cos(2ωt + θ⁻)]
```

Total for phase A:
```
p_a(t) = (V_p / 2)[I_p⁺ cos(θ⁺) + I_p⁻ cos(θ⁻)] 
         - (V_p / 2)[I_p⁺ cos(2ωt + θ⁺) + I_p⁻ cos(2ωt + θ⁻)]
```

Similarly for phases B and C. The total three-phase power:

**DC Component (Average Power):**
```
P_LN_avg = (3/2) V_p [I_p⁺ cos(θ⁺) + I_p⁻ cos(θ⁻)]
```

This is just the **sum** of positive and negative sequence contributions!

**AC Component (2ω ripple):**

For positive sequence alone, the 2ω terms from all three phases cancel.
For negative sequence alone, the 2ω terms also cancel.

**BUT**: When both are present, there is a **beat frequency** interaction!

The 2ω components are:
```
From I+: -I_p⁺ cos(2ωt + θ⁺) [from phase a]
         -I_p⁺ cos(2ωt + θ⁺ - 4π/3) [from phase b]
         -I_p⁺ cos(2ωt + θ⁺ + 4π/3) [from phase c]
         → These sum to zero

From I-: -I_p⁻ cos(2ωt + θ⁻) [from phase a]
         -I_p⁻ cos(2ωt + θ⁻ + 4π/3) [from phase b]
         -I_p⁻ cos(2ωt + θ⁻ - 4π/3) [from phase c]
         → These also sum to zero
```

Wait - let me recalculate this more carefully...

Actually, for phase B with negative sequence:
```
p_b⁻(t) = V_p sin(ωt - 2π/3) · I_p⁻ sin(ωt + θ⁻ + 2π/3)
```

The 2ω term becomes:
```
-cos(2ωt + θ⁻ - 2π/3 + 2π/3) = -cos(2ωt + θ⁻)
```

Hmm, this suggests they should still cancel... Let me verify numerically first.

## Numerical Findings

From the simulation with I⁺ = 200∠0°, I⁻ = 100∠0°:

**P_LN has 2ω ripple!**
- Average: 117.57 kW
- Maximum: 176.36 kW  
- Minimum: 58.79 kW
- **Ripple: 117.58 kW** (100% of average!)

**P_LL also has 2ω ripple!**
- Average: 176.36 kW
- Maximum: 278.19 kW
- Minimum: 74.54 kW
- **Ripple: 203.65 kW**

## Key Insight: Negative Sequence Creates Power Pulsations

The power is no longer constant! The negative sequence introduces a **2ω oscillation** because:

1. Voltage rotates at +ω (CCW)
2. I⁺ component rotates at +ω (CCW) → matches voltage → DC power
3. I⁻ component rotates at -ω (CW) → opposite to voltage → creates 2ω beat

This is analogous to:
- **I⁺**: Co-rotating with voltage → synchronous → DC power
- **I⁻**: Counter-rotating with voltage → creates beat → 2ω ripple

## Revised Power Expression (Hypothesis)

For the case with both sequences, the total power should have the form:

```
P_LN(t) = P_DC + P_2ω cos(2ωt + φ)
```

Where:
```
P_DC = (3/2) V_p [I_p⁺ cos(θ⁺) + I_p⁻ cos(θ⁻)]
```

The 2ω component amplitude depends on the **interference** between I⁺ and I⁻.

## Physical Interpretation

**Positive Sequence Only:**
- Power is constant (DC)
- "Photon-like" packet with steady energy flow
- Allowed window: -60° to +90° (150°)

**With Negative Sequence:**
- Power oscillates at 2ω
- **Instantaneous power can go negative** even when average is positive
- The "photon-like" constraint (P_inst ≥ 0) becomes much more restrictive

**Numerical Result:** Only **25%** of the 2D angle space (θ⁺, θ⁻) allows both P_LN(t) > 0 and P_LL(t) > 0 at all times.

## Implications for CHSH / Quantum Analogy

1. **Negative sequence might represent anti-particles or opposite helicity**
   - Rotates opposite direction
   - Creates interference with positive sequence
   - Can cause power reversal (like pair annihilation?)

2. **The 2ω oscillation is a signature of sequence interference**
   - Beat frequency between forward and backward rotating components
   - Similar to interference patterns in quantum mechanics

3. **Allowed region shrinks dramatically**
   - With I⁺ only: 150° window (42% of angle space)
   - With I⁺ and I⁻: Only 25% of 2D angle space allowed
   - Suggests strong constraints on "physically realizable" states

4. **CHSH angles still matter**
   - Need to check if standard CHSH angles (0°, 22.5°, 45°, 67.5°) remain in allowed region
   - The 2D map shows which combinations of (θ⁺, θ⁻) are permitted

## Next Steps for Full Derivation

Need to:
1. Derive exact expression for 2ω ripple amplitude as function of (I_p⁺, I_p⁻, θ⁺, θ⁻)
2. Find conditions for P_min(t) > 0 in terms of these parameters
3. Map allowed region boundaries analytically
4. Investigate if negative sequence can model entangled pair states

## Speculation: Negative Sequence as "Entanglement"

If positive sequence represents a photon traveling forward, negative sequence could represent:
- Its entangled partner traveling backward (in phase space)
- An anti-particle component
- Opposite polarization/spin state

The 2ω beat pattern might encode the correlation structure!
