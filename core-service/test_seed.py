import sys
print("Test script starting...", flush=True)
sys.stdout.flush()

try:
    from seed_payments import main
    print("Calling main...", flush=True)
    main()
except Exception as e:
    print(f"Error: {e}", flush=True)
    import traceback
    traceback.print_exc()
