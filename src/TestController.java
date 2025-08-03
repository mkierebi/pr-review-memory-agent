package org.prreviewagent;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestParam;

@RestController
public class TestController {

    @GetMapping("/antonio")
    public String antonio(@RequestParam String antonio) {
        // This should trigger the naming rule from review_rules.txt
        return "Hola " + antonio;
    }
}