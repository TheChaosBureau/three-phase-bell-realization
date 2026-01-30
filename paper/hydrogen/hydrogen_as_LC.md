## The Hydrogen Atom as a Distributed LC Resonator

### 1. The Core Reframing

**Standard QM:** Stationary states are solutions of the Schrödinger equation in a Coulomb potential.

**Power-systems view:** The hydrogen atom is a lossless distributed resonator whose normal modes are purely reactive (P=0) standing-wave solutions.

### 2. Identify L and C

**Capacitance** (electric storage): Proton's Coulomb field  
$$u_E = \frac{1}{2}\varepsilon_0 |\mathbf{E}|^2$$

**Inductance** (kinetic storage): Electron inertia  
$$u_K = \frac{1}{2}m|\mathbf{v}|^2$$

Energy sloshes between electric field (C) and kinetic (L) — exactly like an LC tank.

### 3. The Governing Equation

Time-independent Schrödinger:
$$\boxed{ -\frac{\hbar^2}{2m}\nabla^2\phi - \frac{e^2}{4\pi\varepsilon_0 r}\phi = E\,\phi }$$

Rewritten as energy balance:
$$\underbrace{\frac{\hbar^2}{2m}}_{\text{L}}|\nabla\phi|^2 + \underbrace{\frac{e^2}{4\pi\varepsilon_0 r}}_{\text{C}} |\phi|^2= \underbrace{E}_{\text{resonance}}|\phi|^2$$

This is not a force equation — it's an energy balance condition.

### 4. Wavefunction = AC Mode

$$\psi(\mathbf{r},t)=\phi(\mathbf{r})e^{-i\omega t}$$

| QM symbol | Power meaning |
|-----------|---------------|
| $e^{-i\omega t}$ | Steady AC oscillation |
| $\omega = E/\hbar$ | Resonant frequency |
| Eigenstate | Lossless standing mode |

$$\boxed{P = 0} \quad \boxed{Q \neq 0}$$

No real power, only circulating reactive power.

### 5. Why No Radiation

Eigenstates are **standing waves** with no traveling component — no radiation channel, no resistive loss.

Same as: lossless cavity mode, superconducting resonator, perfect LC tank.

### 6. Quantization = Modal Spectrum

Boundary conditions (finite at $r=0$, decay at $r\to\infty$) force discrete resonances:

$$\boxed{ E_n = -\frac{me^4}{2(4\pi\varepsilon_0)^2\hbar^2}\frac{1}{n^2} }$$

Each $n$ is a different LC resonance of the same distributed system.

### 7. Angular Momentum = Circulating Reactive Power

Phase winding $\phi \propto e^{im\theta}$ creates circulating energy flow → quantized orbital angular momentum.

### 8. Photons = Transient Load Coupling

A photon appears only during transitions when the system couples to an external load:

$$\boxed{\Delta E = hf \quad\text{with}\quad P\neq0\ \text{temporarily}}$$

Like dumping energy from an LC tank into a transmission line.

### 9. One-Sentence Takeaway

**The hydrogen atom is a lossless LC resonator whose normal modes are Schrödinger eigenstates, with purely reactive power and zero real power flow.**