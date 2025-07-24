package org.prreviewagent;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController  
public class PaymentController {

    @PostMapping("/payment")
    public String processPayment(String amount) {
        // Similar null handling issue - should trigger auto-review
        if (amount == null) {
            return null;
        }
        
        return "Payment processed: " + amount;
    }
}