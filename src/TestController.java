package org.prreviewagent;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;

@RestController
public class TestController {

    @GetMapping("/test")
    public String test(@RequestParam String input) {
        // This should trigger similarity with stored reviews about validation
        return "Hello " + input;
    }
    
    @GetMapping("/validate")
    public String validate(String data) {
        // Missing validation - should match stored reviews
        return process(data);
    }
    
    private String process(String input) {
        return input.toUpperCase();
    }
}
