window.RSA_FINAL_DATA = {
  "performance": [
    {
      "size": 100,
      "pairwise": 0.06016980000094918,
      "batch": 0.009032899999510846
    },
    {
      "size": 300,
      "pairwise": 0.5301276000009238,
      "batch": 0.04300830000101996
    },
    {
      "size": 1000,
      "pairwise": 6.318308699999761,
      "batch": 0.1925054999992426
    },
    {
      "size": 3000,
      "pairwise": null,
      "batch": 0.7798800999989908
    }
  ],
  "demo": {
    "expected_recoverable_moduli": 5,
    "correctly_factored_moduli": 5,
    "false_positives": 0,
    "false_negatives": 0,
    "invalid_factors": 0,
    "verified_decryption_records": 6,
    "verified_decryption_moduli": 5,
    "invalid_decryptions": [],
    "duplicate_records": 2,
    "passed": true
  },
  "messages": [
    {
      "id": "key-00000",
      "plaintext_utf8": "RSA shared prime lab | key-00000"
    },
    {
      "id": "key-00001",
      "plaintext_utf8": "RSA shared prime lab | key-00001"
    },
    {
      "id": "key-00002",
      "plaintext_utf8": "RSA shared prime lab | key-00002"
    },
    {
      "id": "key-00003",
      "plaintext_utf8": "RSA shared prime lab | key-00003"
    },
    {
      "id": "key-00004",
      "plaintext_utf8": "RSA shared prime lab | key-00004"
    },
    {
      "id": "duplicate-00000",
      "plaintext_utf8": "RSA shared prime lab | duplicate-00000"
    }
  ],
  "input": {
    "schema_version": 1,
    "config": {
      "count": 100,
      "bits": 2048,
      "mode": "demo"
    },
    "record_count": 102,
    "unique_moduli": 100,
    "actual_vulnerable_moduli": 5,
    "actual_weak_fraction": 0.05,
    "generation_seconds": 3.871926900001199,
    "public_sha256": "b40245a8b8c254ebf6c7b0206f8dbca05ecd6f7f24956716b9d9f7f8c91dfbe8",
    "ciphertexts_sha256": "473fff01bd2f925642c9f3c911ee6ad38dab5e189500316d30c0e16bb5fb5032",
    "randomness": "OpenSSL CSPRNG; seed controls pool choices only; replay saved data",
    "source_public_sha256": "833d8d3e823943b9d9792c9f2695c35a8bcc903c688a0e6f3c7554a1dd434727",
    "source_ciphertexts_sha256": "88e636380a915da93163b100753b17fc4320dbd3fafbe2628be0acf9624ae501",
    "archive_line_endings": "UTF-8 LF; original-run byte hashes retained as source_*"
  },
  "repair": {
    "replaced_unique_moduli": 5,
    "affected_records": 6,
    "new_key_roundtrip_records": 6,
    "note": "只验证当前集合共享因子关系；保留原本重复记录的对应关系",
    "original_public_sha256": "833d8d3e823943b9d9792c9f2695c35a8bcc903c688a0e6f3c7554a1dd434727"
  },
  "repaired_found": 0,
  "controls": {
    "summary": {
      "bits": 2048,
      "scan_runs": 10,
      "oaep_negative_checks": 2,
      "passed": true
    },
    "cases": [
      {
        "case": "normal",
        "algorithm": "batch",
        "bits": 2048,
        "records": 100,
        "unique_moduli": 100,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "bf49da0d71707bafa8793d50abd4754de87d5518c041b3ff1804c0a754e66275"
      },
      {
        "case": "normal",
        "algorithm": "pairwise",
        "bits": 2048,
        "records": 100,
        "unique_moduli": 100,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "bf49da0d71707bafa8793d50abd4754de87d5518c041b3ff1804c0a754e66275"
      },
      {
        "case": "duplicates_only",
        "algorithm": "batch",
        "bits": 2048,
        "records": 102,
        "unique_moduli": 100,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "09ae6736e1011cf7c72742547a8b873fd5cea9d68cfd6016b6edf8531c8d6535"
      },
      {
        "case": "duplicates_only",
        "algorithm": "pairwise",
        "bits": 2048,
        "records": 102,
        "unique_moduli": 100,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "09ae6736e1011cf7c72742547a8b873fd5cea9d68cfd6016b6edf8531c8d6535"
      },
      {
        "case": "isolated_target",
        "algorithm": "batch",
        "bits": 2048,
        "records": 1,
        "unique_moduli": 1,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "274ef6d15dae7626ba46c47e3b9a068ee91810cb7416acb40d536fe657f27e72"
      },
      {
        "case": "isolated_target",
        "algorithm": "pairwise",
        "bits": 2048,
        "records": 1,
        "unique_moduli": 1,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "274ef6d15dae7626ba46c47e3b9a068ee91810cb7416acb40d536fe657f27e72"
      },
      {
        "case": "shared_prime_demo",
        "algorithm": "batch",
        "bits": 2048,
        "records": 102,
        "unique_moduli": 100,
        "expected_recoverable": 5,
        "correctly_factored": 5,
        "verified_messages": 6,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "833d8d3e823943b9d9792c9f2695c35a8bcc903c688a0e6f3c7554a1dd434727"
      },
      {
        "case": "shared_prime_demo",
        "algorithm": "pairwise",
        "bits": 2048,
        "records": 102,
        "unique_moduli": 100,
        "expected_recoverable": 5,
        "correctly_factored": 5,
        "verified_messages": 6,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "833d8d3e823943b9d9792c9f2695c35a8bcc903c688a0e6f3c7554a1dd434727"
      },
      {
        "case": "repaired",
        "algorithm": "batch",
        "bits": 2048,
        "records": 102,
        "unique_moduli": 100,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "5c97b4a7d8e4cab634a311005266de3c24fa6e004d0d8847239e8722d31824f2"
      },
      {
        "case": "repaired",
        "algorithm": "pairwise",
        "bits": 2048,
        "records": 102,
        "unique_moduli": 100,
        "expected_recoverable": 0,
        "correctly_factored": 0,
        "verified_messages": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "passed": true,
        "public_sha256": "5c97b4a7d8e4cab634a311005266de3c24fa6e004d0d8847239e8722d31824f2"
      }
    ],
    "oaep_checks": [
      {
        "case": "wrong_oaep_label",
        "expected": "invalid_ciphertext",
        "observed": "invalid_ciphertext",
        "passed": true
      },
      {
        "case": "corrupted_ciphertext",
        "expected": "invalid_ciphertext",
        "observed": "invalid_ciphertext",
        "passed": true
      }
    ],
    "repair_legitimate_roundtrips": 6
  },
  "reconstruction": {
    "id": "key-00000",
    "bits": 2048,
    "e": 65537,
    "p_bits": 1024,
    "q_bits": 1024,
    "factor_product_verified": true,
    "inverse_verified": true
  },
  "stages": {
    "preprocess": 0.004850000001169974,
    "conversion": 0.0014200999994500307,
    "product_tree": 0.06187169999975595,
    "remainder_tree": 0.6618211000004521,
    "final_gcd": 0.040989500001160195,
    "fallback": 5.000001692678779e-07,
    "assemble": 0.004819300000235671
  },
  "pool": [
    {
      "size": 4,
      "median": 1.0
    },
    {
      "size": 16,
      "median": 0.9666666666666667
    },
    {
      "size": 64,
      "median": 0.55
    }
  ],
  "fallback_candidates": 3,
  "fallback_checks": 9,
  "benchmark_config": {
    "sizes": [
      100,
      300,
      1000,
      3000
    ],
    "repeats": 3,
    "worker_timeout_seconds": 45.0,
    "backend": "gmpy2",
    "timeout_scope": "whole subprocess including startup, I/O and scan; timed-out scan seconds left empty"
  }
};
