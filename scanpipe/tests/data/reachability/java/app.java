import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Map;

public class App {
    public static boolean debug = true;

    public static class ReportGenerator {
        private String baseDir;

        public ReportGenerator(String baseDir) {
            this.baseDir = baseDir;
        }

        public String getBaseDir() {
            return baseDir;
        }
    }

    public static String serveReport(Map<String, String> requestPayload) {
        ReportGenerator generator = new ReportGenerator("/var/reports");
        String requestedFile = requestPayload.get("file");

        if (requestedFile == null || requestedFile.isEmpty()) {
            return "Error: No file specified";
        }

        // VULNERABLE: Direct concatenation allows Path Traversal
        // An attacker passing "../../etc/passwd" could read system files.
        String targetPath = buildFilePath(generator, requestedFile);

        try {
            if (Files.exists(Paths.get(targetPath))) {
                return "Serving content of " + targetPath;
            }
        } catch (Exception e) {
            return "Error: Invalid path";
        }

        return "Error: File not found";
    }

    private static String buildFilePath(ReportGenerator generator, String filename) {
        return Paths.get(generator.getBaseDir(), filename).toString();
    }

    public static String unrelatedTopLevelFunction() {
        return "I am just here to add AST complexity.";
    }
}