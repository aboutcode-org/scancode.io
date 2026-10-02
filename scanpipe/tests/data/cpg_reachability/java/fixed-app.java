import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;

public class App {
    public static boolean debug = false;

    public static class ReportGenerator {
        public String baseDir;

        public ReportGenerator(String baseDir) {
            this.baseDir = baseDir;
        }
    }

    public static String serveReport(Map<String, String> requestPayload) {
        ReportGenerator generator = new ReportGenerator("/var/reports");
        String requestedFile = requestPayload.get("file");

        if (requestedFile == null || requestedFile.isEmpty()) {
            return "Error: No file specified";
        }

        String targetPath;
        try {
            targetPath = buildFilePath(generator, requestedFile);
        } catch (Exception e) {
            return "Error: Invalid path";
        }

        try {
            if (Files.exists(Paths.get(targetPath))) {
                return "Serving content of " + targetPath;
            }
        } catch (Exception e) {
            return "Error: Invalid path";
        }

        return "Error: File not found";
    }

    /**
     * FIXED: Validate that the resolved path stays within the base_dir
     */
    private static String buildFilePath(ReportGenerator generator, String filename) throws Exception {
        Path base = Paths.get(generator.baseDir).toAbsolutePath().normalize();
        Path target = Paths.get(generator.baseDir, filename).toAbsolutePath().normalize();

        if (!target.startsWith(base)) {
            throw new Exception("Path Traversal Detected");
        }
        return target.toString();
    }


    public static String unrelatedTopLevelFunction() {
        return "I am just here to add AST complexity.";
    }
}