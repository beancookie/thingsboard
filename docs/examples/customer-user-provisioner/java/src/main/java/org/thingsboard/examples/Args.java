package org.thingsboard.examples;

import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

final class Args {
    private final Map<String, String> values = new HashMap<>();
    private final Set<String> flags = new HashSet<>();

    Args(String[] args) {
        for (int i = 0; i < args.length; i++) {
            String arg = args[i];
            if (!arg.startsWith("--")) {
                continue;
            }
            String key = arg.substring(2);
            if (key.contains("=")) {
                String[] parts = key.split("=", 2);
                values.put(parts[0], parts[1]);
            } else if (i + 1 < args.length && !args[i + 1].startsWith("--")) {
                values.put(key, args[++i]);
            } else {
                flags.add(key);
            }
        }
    }

    String get(String key, String def) {
        return values.getOrDefault(key, def);
    }

    boolean has(String key) {
        return values.containsKey(key) || flags.contains(key);
    }
}
