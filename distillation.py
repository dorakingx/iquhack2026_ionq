"""
Iterative DEJMPS Entanglement Distillation Protocol Implementation

This module implements the Iterative DEJMPS (Dür, Ekert, Jozsa, Macchiavello, Popescu, Sanpera)
entanglement distillation protocol for purifying noisy Bell pairs.
"""

from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit import qasm3
import numpy as np


def create_distillation_circuit(num_bell_pairs: int) -> QuantumCircuit:
    """
    Creates a Qiskit QuantumCircuit implementing Iterative DEJMPS Entanglement Distillation.
    
    The protocol iteratively purifies a target Bell pair using ancilla pairs. For each
    ancilla pair k (from 0 to N-2), the protocol:
    1. Applies local rotations (twirling) to both target and ancilla qubits
    2. Performs CNOT gates (LOCC operations)
    3. Measures ancilla qubits and checks if measurements match (parity check)
    4. Sets a flag bit to 1 if any step fails (measurements don't match)
    
    Qubit Mapping:
    - Total qubits: 2N
    - Alice's register: qubits 0 to N-1
    - Bob's register: qubits N to 2N-1
    - Pair k: Alice[k] paired with Bob[2N-1-k] (outside-in pairing)
    - Target pair (output): Alice[N-1] and Bob[N] (innermost pair)
    - Ancilla pairs: k = 0 to N-2 (all outer pairs)
    
    Args:
        num_bell_pairs: Number of Bell pairs N (2 <= N <= 8)
        
    Returns:
        QuantumCircuit: Qiskit circuit implementing the distillation protocol.
                       The circuit includes a `_modified_qasm3` attribute containing
                       the OpenQASM 3.0 string with flag logic, and a `get_qasm3_with_flag()`
                       method to retrieve it. Use `qc._modified_qasm3` or `qc.get_qasm3_with_flag()`
                       when submitting to the server instead of `qasm3.dumps(qc)`.
        
    Raises:
        ValueError: If num_bell_pairs is not between 2 and 8
        
    Example:
        >>> qc = create_distillation_circuit(2)
        >>> # Use the modified OpenQASM 3.0 string with flag logic
        >>> qasm_str = qc.get_qasm3_with_flag()
        >>> # Or access directly:
        >>> qasm_str = qc._modified_qasm3
    """
    # Validate input
    if not (2 <= num_bell_pairs <= 8):
        raise ValueError("num_bell_pairs must be between 2 and 8")
    
    N = num_bell_pairs
    
    # Create registers
    # Total qubits: 2N (Alice: 0..N-1, Bob: N..2N-1)
    qr = QuantumRegister(2*N, 'q')
    # Classical register: 2*(N-1) for measurements + 1 flag bit = 2N-1 total
    cr = ClassicalRegister(2*N-1, 'c')
    qc = QuantumCircuit(qr, cr)
    
    # Target pair indices (innermost pair - the output)
    alice_target = N - 1
    bob_target = N
    
    # Flag bit index (last classical bit)
    flag_bit = 2*N - 2
    
    # Iterate through each ancilla pair k (from 0 to N-2)
    for k in range(N - 1):
        # Ancilla pair indices
        alice_ancilla = k
        bob_ancilla = 2*N - 1 - k
        
        # Classical bit indices for measurements
        alice_meas = 2*k
        bob_meas = 2*k + 1
        
        # Step 1: Twirling (Local Rotations)
        # Alice applies R_x(π/2) to target and ancilla
        qc.rx(np.pi/2, qr[alice_target])
        qc.rx(np.pi/2, qr[alice_ancilla])
        
        # Bob applies R_x(-π/2) to target and ancilla
        qc.rx(-np.pi/2, qr[bob_target])
        qc.rx(-np.pi/2, qr[bob_ancilla])
        
        # Step 2: CNOT Gates (LOCC operations)
        # Alice: CNOT(control=ancilla, target=target)
        qc.cx(qr[alice_ancilla], qr[alice_target])
        # Bob: CNOT(control=ancilla, target=target)
        qc.cx(qr[bob_ancilla], qr[bob_target])
        
        # Step 3: Measurement & Parity Check
        # Measure Alice's ancilla qubit
        qc.measure(qr[alice_ancilla], cr[alice_meas])
        # Measure Bob's ancilla qubit
        qc.measure(qr[bob_ancilla], cr[bob_meas])
    
    # Step 4: Flag Logic - Add classical operations using OpenQASM 3.0 string manipulation
    # Convert circuit to OpenQASM 3.0 string
    qasm_str = qasm3.dumps(qc)
    
    # Add flag logic: for each step, check if measurements don't match
    # Flag should be 1 if ANY step fails (measurements don't match)
    flag_logic_lines = []
    flag_logic_lines.append("    // Flag logic: set flag = 1 if any measurements don't match")
    
    # For each distillation step, check if measurements match
    for k in range(N - 1):
        alice_meas = 2*k
        bob_meas = 2*k + 1
        flag_logic_lines.append(f"    // Step {k}: Check if c[{alice_meas}] != c[{bob_meas}]")
        # Check both mismatch cases using OpenQASM 3.0 conditionals
        flag_logic_lines.append(f"    if (c[{alice_meas}] == true && c[{bob_meas}] == false) {{")
        flag_logic_lines.append(f"        c[{flag_bit}] = true;")
        flag_logic_lines.append(f"    }}")
        flag_logic_lines.append(f"    if (c[{alice_meas}] == false && c[{bob_meas}] == true) {{")
        flag_logic_lines.append(f"        c[{flag_bit}] = true;")
        flag_logic_lines.append(f"    }}")
    
    # Insert flag logic before the final closing brace
    qasm_lines = qasm_str.split('\n')
    
    # Find the last closing brace (end of circuit body)
    insert_pos = len(qasm_lines)
    for i in range(len(qasm_lines) - 1, -1, -1):
        stripped = qasm_lines[i].strip()
        if stripped == '}' and i > 0:  # Found a closing brace (but not the very last one)
            insert_pos = i
            break
    
    # Insert flag logic
    new_qasm_lines = qasm_lines[:insert_pos] + flag_logic_lines + qasm_lines[insert_pos:]
    new_qasm_str = '\n'.join(new_qasm_lines)
    
    # Store the modified OpenQASM 3.0 string as an attribute
    # Since Qiskit doesn't easily support parsing OpenQASM 3.0 with classical operations
    # back into QuantumCircuit, we store the modified string for use when submitting
    qc._modified_qasm3 = new_qasm_str
    
    # Create a helper method to get the OpenQASM 3.0 string with flag logic
    def get_qasm3_with_flag():
        """Get the OpenQASM 3.0 string with flag logic included."""
        return new_qasm_str
    
    qc.get_qasm3_with_flag = get_qasm3_with_flag
    
    return qc
